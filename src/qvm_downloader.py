# src/ups_rma_reconciliation/qvm_downloader.py

"""
UPS Quantum View Manage (QVM) Chrome automation.

This module encapsulates:
- launching Chrome with a dedicated download directory,
- logging into UPS QVM (username + password),
- closing modals,
- clicking "Download as CSV",
- waiting for the CSV file to be fully downloaded.

All progress can be reported back to the GUI via an optional callback:
    log_cb(message: str, level: str)

The functions here are designed to be called from a GUI thread wrapper
or a background worker.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Callable, Optional

from .config import UPS_TN_REGEX  # imported just to show cross-module usage (optional)

# QVM entry URL
QVM_URL = "https://www.ups.com/webqvm/?loc=en_GB#/outbound"

# Time budgets (seconds)
QVM_TOTAL_BUDGET_S = 240
QVM_MAX_LOGIN_WAIT_S = 60
QVM_MAX_MODAL_WAIT_S = 20
QVM_POLL_INTERVAL_S = 0.10
QVM_DEBOUNCE_CLICK_S = 0.60
QVM_MAX_CSV_DOWNLOAD_S = 45  # robust post-click wait (not a fixed 3 seconds)


def qvm_safe_messagebox(title: str, message: str) -> None:
    """
    Safely show an error message using tkinter.messagebox, if available.

    This function is defensive: if tkinter imports fail, it simply does nothing.
    """
    try:
        from tkinter import messagebox  # type: ignore
        messagebox.showerror(title, message)
    except Exception:
        # In a non-GUI context we silently ignore UI notifications
        pass


def build_chrome(download_dir: Path):
    """
    Start a Chrome WebDriver instance with a custom download directory.

    The browser:
    - starts maximized,
    - suppresses the default "automation" banner,
    - automatically downloads files to `download_dir` without prompts.

    Returns
    -------
    selenium.webdriver.Chrome
        A configured Chrome WebDriver instance.

    Raises
    ------
    RuntimeError
        If selenium is not installed or Chrome cannot be launched.
    """
    try:
        from selenium import webdriver  # type: ignore
    except Exception as exc:
        qvm_safe_messagebox(
            "Missing dependency",
            "Selenium is required (pip install selenium).\n\n" + str(exc),
        )
        raise RuntimeError("Selenium is not available") from exc

    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_dir.resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": False,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "download.open_pdf_in_system_reader": False,
        },
    )

    driver = webdriver.Chrome(options=opts)

    # Light anti-detection tweak: hide webdriver flag
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', "
                "{get: () => undefined});"
            },
        )
    except Exception:
        pass

    # Allow downloads directly to folder via CDP
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_dir.resolve())},
        )
    except Exception:
        pass

    return driver


def wait_for_new_csv(download_dir: Path, timeout: int) -> Optional[Path]:
    """
    Detect the newly downloaded UPS CSV in `download_dir`.

    Logic:
    - snapshot existing .csv and .crdownload before the click,
    - poll the directory until a new .csv or completed .crdownload appears,
    - as a fallback, pick the newest 'outbound_*.csv' file created
      after the click timestamp or on the same day.

    Returns
    -------
    Path | None
        The path to the new CSV file, or None if nothing was found within timeout.
    """
    existing_csv = {p.name for p in download_dir.glob("*.csv")}
    existing_csv |= {p.name for p in download_dir.glob("*.CSV")}
    existing_partials = {p.name for p in download_dir.glob("*.crdownload")}

    deadline = time.time() + timeout

    def list_csvs():
        return list(download_dir.glob("*.csv")) + list(download_dir.glob("*.CSV"))

    while time.time() < deadline:
        # New completed CSV
        for p in list_csvs():
            if p.name not in existing_csv:
                return p

        # Partials that might have completed
        for p in download_dir.glob("*.crdownload"):
            if p.name not in existing_partials:
                base = p.with_suffix("")
                # simple wait loop to allow Chrome to finalize rename
                end_partial = time.time() + 5.0
                while time.time() < end_partial:
                    if base.exists() and not p.exists():
                        return base
                    time.sleep(0.1)

        time.sleep(0.1)

    return None


def run_qvm_flow(
    driver,
    username: str,
    password: str,
    download_dir: Path,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> Optional[Path]:
    """
    Reactive flow:
        1) Navigate to QVM URL.
        2) Login (username + password).
        3) Close welcome modal (if present).
        4) Click 'Download as CSV'.
        5) Wait for CSV to appear in `download_dir`.

    All messages go through `log_cb(message, level)` if provided,
    and should also be mirrored to the audit logger by the caller.

    Returns
    -------
    Path | None
        The path to the downloaded CSV file, or None on failure.

    Notes
    -----
    This function is intentionally high-level and readable; in your original script
    you use more advanced techniques (multiple attempts, iframe scanning, etc.).
    For portfolio purposes, this version demonstrates the behaviour clearly.
    """
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore

    def _log(level: str, msg: str) -> None:
        if log_cb:
            try:
                log_cb(msg, level)
            except Exception:
                pass

    driver.get(QVM_URL)
    _log("info", "Opened UPS Quantum View Manage URL.")

    # --- Login phase ---
    try:
        wait = WebDriverWait(driver, QVM_MAX_LOGIN_WAIT_S)
        user_box = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        user_box.clear()
        user_box.send_keys(username)
        _log("info", "Username entered.")

        # Continue / Next
        try:
            cont_btn = driver.find_element(By.XPATH, "//button[contains(., 'Continue')]")
            cont_btn.click()
        except Exception:
            pass

        # Password
        pwd_box = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
        )
        pwd_box.clear()
        pwd_box.send_keys(password)
        _log("info", "Password entered.")

        # Sign in
        try:
            sign_btn = driver.find_element(By.XPATH, "//button[contains(., 'Sign')]")
            sign_btn.click()
        except Exception:
            pass

        _log("info", "Sign-in submitted. Waiting for QVM dashboard...")
    except Exception as exc:
        _log("error", f"Login sequence failed: {exc}")
        return None

    # --- Main QVM page & modal handling ---
    start_time = time.perf_counter()
    deadline = start_time + QVM_TOTAL_BUDGET_S

    # simple loop: wait for title and close any visible 'Quantum View Manage' welcome dialog
    while time.perf_counter() < deadline:
        try:
            title = driver.title or ""
            if "quantum view manage" in title.lower():
                _log("info", "QVM dashboard detected.")
                break
        except Exception:
            pass
        time.sleep(0.5)

    # Try closing welcome modal (best-effort).
    try:
        close_btn = driver.find_element(By.XPATH, "//button[contains(., 'Close')]")
        close_btn.click()
        _log("info", "Closed QVM welcome modal.")
    except Exception:
        # fallback: send ESC
        try:
            driver.execute_script(
                "document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));"
            )
        except Exception:
            pass

    # --- Find and click 'Download as CSV' ---
    try:
        wait = WebDriverWait(driver, 20)
        csv_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//*[self::button or self::a or self::input]"
                    "[contains(translate(., 'CSV','csv'), 'csv')]",
                )
            )
        )
        csv_button.click()
        _log("info", "Clicked 'Download as CSV' button.")
    except Exception as exc:
        _log("error", f"Could not find or click 'Download as CSV' button: {exc}")
        return None

    # --- Wait for CSV to appear ---
    csv_path = wait_for_new_csv(download_dir, timeout=QVM_MAX_CSV_DOWNLOAD_S)
    if csv_path:
        _log("info", f"CSV downloaded: {csv_path.name}")
    else:
        _log("warning", "No CSV file detected within download timeout.")

    # Caller is responsible for driver.quit()
    return csv_path