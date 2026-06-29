# =============================================================================
# ITC Face Recognition — database_tools.py
# Standalone developer utility for managing the PostgreSQL database.
# Usage: python database_tools.py
# =============================================================================

import os
import sys
import platform
from datetime import datetime

# Third-party
try:
    from colorama import Fore, Back, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    print("colorama is not installed. Run: pip install colorama")
    sys.exit(1)

# Local — reuse the project's existing connection helper
try:
    from database import get_connection
except ImportError:
    print("ERROR: database.py not found. Run this script from your project root.")
    sys.exit(1)


# =============================================================================
# TERMINAL HELPERS
# =============================================================================

def clear_screen() -> None:
    """Clear the terminal screen — cross-platform."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def pause() -> None:
    """Wait for the user to press Enter before returning to the menu."""
    print()
    input(Fore.CYAN + "  Press Enter to continue…" + Style.RESET_ALL)


def hr(char: str = "─", width: int = 60) -> str:
    """Return a horizontal rule string."""
    return char * width


def header(title: str) -> None:
    """Print a styled section header."""
    print()
    print(Fore.CYAN + hr("═"))
    print(Fore.CYAN + Style.BRIGHT + f"  {title}")
    print(Fore.CYAN + hr("═"))
    print()


def success(msg: str) -> None:
    print(Fore.GREEN + Style.BRIGHT + f"  ✓  {msg}" + Style.RESET_ALL)


def warn(msg: str) -> None:
    print(Fore.YELLOW + f"  ⚠  {msg}" + Style.RESET_ALL)


def error(msg: str) -> None:
    print(Fore.RED + Style.BRIGHT + f"  ✗  {msg}" + Style.RESET_ALL)


def info(msg: str) -> None:
    print(Fore.BLUE + f"  ℹ  {msg}" + Style.RESET_ALL)


def col(text: str, width: int, align: str = "<") -> str:
    """Return a fixed-width column string."""
    text = str(text) if text is not None else "—"
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"{text:{align}{width}}"


def confirm(prompt: str = "Are you sure?") -> bool:
    """Ask Y/N and return True only on 'Y' or 'y'."""
    answer = input(Fore.YELLOW + f"  {prompt} (Y/N): " + Style.RESET_ALL).strip()
    return answer.upper() == "Y"


# =============================================================================
# MENU
# =============================================================================

def print_menu() -> None:
    """Render the main menu."""
    clear_screen()
    print()
    print(Fore.CYAN + Style.BRIGHT + hr("═"))
    print(Fore.CYAN + Style.BRIGHT + "       ITC FACE RECOGNITION — DATABASE TOOLS")
    print(Fore.CYAN + Style.BRIGHT + hr("═"))
    print()
    print(Fore.WHITE + "  VIEW")
    print(f"    {Fore.GREEN}1{Fore.WHITE}  Show Registered Customers")
    print(f"    {Fore.GREEN}2{Fore.WHITE}  Show Unknown Customers")
    print(f"    {Fore.GREEN}3{Fore.WHITE}  Show Visit Logs")
    print(f"    {Fore.GREEN}4{Fore.WHITE}  Show Daily Statistics")
    print()
    print(Fore.WHITE + "  DELETE (single row)")
    print(f"    {Fore.YELLOW}5{Fore.WHITE}  Delete a Registered Customer")
    print(f"    {Fore.YELLOW}6{Fore.WHITE}  Delete an Unknown Customer")
    print()
    print(Fore.WHITE + "  RESET (entire table)")
    print(f"    {Fore.RED}7{Fore.WHITE}   Reset Registered Customers")
    print(f"    {Fore.RED}8{Fore.WHITE}   Reset Unknown Customers")
    print(f"    {Fore.RED}9{Fore.WHITE}   Reset Visit Logs")
    print(f"    {Fore.RED}10{Fore.WHITE}  Reset Daily Statistics")
    print()
    print(f"    {Fore.RED + Style.BRIGHT}11{Style.RESET_ALL}  {Fore.RED}Reset ENTIRE Database")
    print()
    print(Fore.WHITE + "  TOOLS")
    print(f"    {Fore.BLUE}12{Fore.WHITE}  Database Summary")
    print(f"    {Fore.BLUE}13{Fore.WHITE}  Show Database Structure")
    print(f"    {Fore.BLUE}14{Fore.WHITE}  Export Database Report")
    print()
    print(f"    {Fore.WHITE}15  Exit")
    print()
    print(Fore.CYAN + hr("═"))


# =============================================================================
# OPTION 1 — Show Registered Customers
# =============================================================================

def show_registered_customers() -> None:
    """Display all rows in the customers table."""
    clear_screen()
    header("REGISTERED CUSTOMERS")

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, name, email, phone, visit_count, created_at, last_seen
            FROM customers
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            warn("No registered customers found.")
            pause()
            return

        # Table header
        print(
            Fore.YELLOW + Style.BRIGHT
            + col("ID", 6)
            + col("Name", 22)
            + col("Email", 28)
            + col("Phone", 18)
            + col("Visits", 8)
            + col("Created", 22)
            + col("Last Seen", 22)
        )
        print(Fore.CYAN + hr("─", 126))

        for row in rows:
            (rid, name, email, phone, visits, created, last_seen) = row
            created_str  = created.strftime("%Y-%m-%d %H:%M")  if created  else "—"
            last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M") if last_seen else "—"
            print(
                Fore.WHITE
                + col(rid, 6)
                + col(name, 22)
                + col(email or "—", 28)
                + col(phone or "—", 18)
                + col(visits, 8)
                + col(created_str, 22)
                + col(last_seen_str, 22)
            )

        print(Fore.CYAN + hr("─", 126))
        info(f"Total: {len(rows)} customer(s)")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 2 — Show Unknown Customers
# =============================================================================

def show_unknown_customers() -> None:
    """Display all rows in the unknown_customers table."""
    clear_screen()
    header("UNKNOWN CUSTOMERS")

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, visit_count, first_seen, last_seen
            FROM unknown_customers
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            warn("No unknown customers on record.")
            pause()
            return

        print(
            Fore.YELLOW + Style.BRIGHT
            + col("ID", 8)
            + col("Visits", 10)
            + col("First Seen", 24)
            + col("Last Seen", 24)
        )
        print(Fore.CYAN + hr("─", 66))

        for row in rows:
            (rid, visits, first_seen, last_seen) = row
            first_str = first_seen.strftime("%Y-%m-%d %H:%M:%S") if first_seen else "—"
            last_str  = last_seen.strftime("%Y-%m-%d %H:%M:%S")  if last_seen  else "—"
            print(
                Fore.WHITE
                + col(rid, 8)
                + col(visits, 10)
                + col(first_str, 24)
                + col(last_str, 24)
            )

        print(Fore.CYAN + hr("─", 66))
        info(f"Total: {len(rows)} unknown customer(s)")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 3 — Show Visit Logs
# =============================================================================

def show_visit_logs() -> None:
    """Display all rows in visit_logs, newest first."""
    clear_screen()
    header("VISIT LOGS  (newest first)")

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, customer_type, customer_id, visit_time
            FROM visit_logs
            ORDER BY id DESC
            LIMIT 200
            """
        )
        rows = cur.fetchall()

        # Count total for info line
        cur.execute("SELECT COUNT(*) FROM visit_logs")
        total = cur.fetchone()[0]
        cur.close()
        conn.close()

        if not rows:
            warn("No visit logs found.")
            pause()
            return

        print(
            Fore.YELLOW + Style.BRIGHT
            + col("ID", 8)
            + col("Type", 20)
            + col("Customer ID", 14)
            + col("Visit Time", 24)
        )
        print(Fore.CYAN + hr("─", 66))

        for row in rows:
            (lid, ctype, cid, vtime) = row
            time_str = vtime.strftime("%Y-%m-%d %H:%M:%S") if vtime else "—"

            # Colour-code by type
            if ctype == "known":
                type_coloured = Fore.GREEN + col(ctype, 20) + Fore.WHITE
            elif ctype == "returning_unknown":
                type_coloured = Fore.YELLOW + col(ctype, 20) + Fore.WHITE
            else:
                type_coloured = Fore.RED + col(ctype, 20) + Fore.WHITE

            print(
                Fore.WHITE
                + col(lid, 8)
                + type_coloured
                + col(cid, 14)
                + col(time_str, 24)
            )

        print(Fore.CYAN + hr("─", 66))
        if total > 200:
            info(f"Showing latest 200 of {total} total log entries.")
        else:
            info(f"Total: {total} log entry/entries.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 4 — Show Daily Statistics
# =============================================================================

def show_daily_statistics() -> None:
    """Display all rows in daily_statistics."""
    clear_screen()
    header("DAILY STATISTICS")

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT stat_date, known_today, unknown_today, returning_unknown_today
            FROM daily_statistics
            ORDER BY stat_date DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            warn("No daily statistics recorded yet.")
            pause()
            return

        print(
            Fore.YELLOW + Style.BRIGHT
            + col("Date", 16)
            + col("Known", 12)
            + col("Unknown", 12)
            + col("Returning", 14)
        )
        print(Fore.CYAN + hr("─", 54))

        for row in rows:
            (stat_date, known, unknown, returning) = row
            date_str = stat_date.isoformat() if hasattr(stat_date, "isoformat") else str(stat_date)
            print(
                Fore.WHITE
                + col(date_str, 16)
                + Fore.GREEN  + col(known,     12) + Fore.WHITE
                + Fore.RED    + col(unknown,   12) + Fore.WHITE
                + Fore.YELLOW + col(returning, 14) + Fore.WHITE
            )

        print(Fore.CYAN + hr("─", 54))
        info(f"Total: {len(rows)} day(s) on record.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 5 — Delete a Registered Customer
# =============================================================================

def delete_customer() -> None:
    """Interactively delete a single registered customer and their visit logs."""
    clear_screen()
    header("DELETE REGISTERED CUSTOMER")

    try:
        conn = get_connection()
        cur  = conn.cursor()

        # Show current customer list first
        cur.execute("SELECT id, name, email, visit_count FROM customers ORDER BY id ASC")
        rows = cur.fetchall()

        if not rows:
            warn("No registered customers to delete.")
            cur.close()
            conn.close()
            pause()
            return

        print(Fore.YELLOW + Style.BRIGHT + col("ID", 6) + col("Name", 24) + col("Email", 30) + col("Visits", 8))
        print(Fore.CYAN + hr("─", 68))
        for (rid, name, email, visits) in rows:
            print(Fore.WHITE + col(rid, 6) + col(name, 24) + col(email or "—", 30) + col(visits, 8))
        print(Fore.CYAN + hr("─", 68))
        print()

        try:
            target_id = int(input(Fore.CYAN + "  Enter Customer ID to delete (0 to cancel): " + Style.RESET_ALL).strip())
        except ValueError:
            warn("Invalid input. Returning to menu.")
            cur.close()
            conn.close()
            pause()
            return

        if target_id == 0:
            info("Cancelled.")
            cur.close()
            conn.close()
            pause()
            return

        # Verify the ID exists
        cur.execute("SELECT name FROM customers WHERE id = %s", (target_id,))
        result = cur.fetchone()
        if not result:
            error(f"No customer found with ID {target_id}.")
            cur.close()
            conn.close()
            pause()
            return

        customer_name = result[0]
        print()
        warn(f"You are about to delete '{customer_name}' (ID {target_id}) and all their visit logs.")

        if not confirm("Confirm deletion"):
            info("Deletion cancelled.")
            cur.close()
            conn.close()
            pause()
            return

        # Delete related visit logs first (referential integrity)
        cur.execute(
            "DELETE FROM visit_logs WHERE customer_type = 'known' AND customer_id = %s",
            (target_id,)
        )
        logs_deleted = cur.rowcount

        # Delete the customer
        cur.execute("DELETE FROM customers WHERE id = %s", (target_id,))

        conn.commit()
        cur.close()
        conn.close()

        success(f"Customer '{customer_name}' deleted.")
        info(f"Also removed {logs_deleted} related visit log(s).")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 6 — Delete an Unknown Customer
# =============================================================================

def delete_unknown_customer() -> None:
    """Interactively delete a single unknown customer."""
    clear_screen()
    header("DELETE UNKNOWN CUSTOMER")

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute(
            "SELECT id, visit_count, first_seen, last_seen FROM unknown_customers ORDER BY id ASC"
        )
        rows = cur.fetchall()

        if not rows:
            warn("No unknown customers to delete.")
            cur.close()
            conn.close()
            pause()
            return

        print(Fore.YELLOW + Style.BRIGHT + col("ID", 8) + col("Visits", 10) + col("First Seen", 24) + col("Last Seen", 24))
        print(Fore.CYAN + hr("─", 66))
        for (rid, visits, first_seen, last_seen) in rows:
            print(
                Fore.WHITE
                + col(rid, 8)
                + col(visits, 10)
                + col(first_seen.strftime("%Y-%m-%d %H:%M") if first_seen else "—", 24)
                + col(last_seen.strftime("%Y-%m-%d %H:%M")  if last_seen  else "—", 24)
            )
        print(Fore.CYAN + hr("─", 66))
        print()

        try:
            target_id = int(input(Fore.CYAN + "  Enter Unknown Customer ID to delete (0 to cancel): " + Style.RESET_ALL).strip())
        except ValueError:
            warn("Invalid input. Returning to menu.")
            cur.close()
            conn.close()
            pause()
            return

        if target_id == 0:
            info("Cancelled.")
            cur.close()
            conn.close()
            pause()
            return

        cur.execute("SELECT id FROM unknown_customers WHERE id = %s", (target_id,))
        if not cur.fetchone():
            error(f"No unknown customer found with ID {target_id}.")
            cur.close()
            conn.close()
            pause()
            return

        print()
        warn(f"You are about to delete unknown customer ID {target_id} and their visit logs.")

        if not confirm("Confirm deletion"):
            info("Deletion cancelled.")
            cur.close()
            conn.close()
            pause()
            return

        # Delete related visit logs
        cur.execute(
            "DELETE FROM visit_logs WHERE customer_type IN ('unknown', 'returning_unknown') AND customer_id = %s",
            (target_id,)
        )
        logs_deleted = cur.rowcount

        cur.execute("DELETE FROM unknown_customers WHERE id = %s", (target_id,))

        conn.commit()
        cur.close()
        conn.close()

        success(f"Unknown customer ID {target_id} deleted.")
        info(f"Also removed {logs_deleted} related visit log(s).")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 7 — Reset Registered Customers
# =============================================================================

def reset_registered() -> None:
    """Delete all registered customers and reset the SERIAL sequence."""
    clear_screen()
    header("RESET REGISTERED CUSTOMERS")

    warn("This will permanently delete ALL registered customers and their visit logs.")
    print()

    if not confirm("Are you absolutely sure"):
        info("Reset cancelled.")
        pause()
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        # Remove related known visit logs
        cur.execute("DELETE FROM visit_logs WHERE customer_type = 'known'")
        logs_deleted = cur.rowcount

        # Delete all customers
        cur.execute("DELETE FROM customers")
        rows_deleted = cur.rowcount

        # Reset the SERIAL sequence
        cur.execute("ALTER SEQUENCE customers_id_seq RESTART WITH 1")

        conn.commit()
        cur.close()
        conn.close()

        success(f"Deleted {rows_deleted} registered customer(s).")
        info(f"Also removed {logs_deleted} related visit log(s).")
        success("SERIAL ID sequence reset to 1.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 8 — Reset Unknown Customers
# =============================================================================

def reset_unknown() -> None:
    """Delete all unknown customers and reset the SERIAL sequence."""
    clear_screen()
    header("RESET UNKNOWN CUSTOMERS")

    warn("This will permanently delete ALL unknown customers and their visit logs.")
    print()

    if not confirm("Are you absolutely sure"):
        info("Reset cancelled.")
        pause()
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("DELETE FROM visit_logs WHERE customer_type IN ('unknown', 'returning_unknown')")
        logs_deleted = cur.rowcount

        cur.execute("DELETE FROM unknown_customers")
        rows_deleted = cur.rowcount

        cur.execute("ALTER SEQUENCE unknown_customers_id_seq RESTART WITH 1")

        conn.commit()
        cur.close()
        conn.close()

        success(f"Deleted {rows_deleted} unknown customer(s).")
        info(f"Also removed {logs_deleted} related visit log(s).")
        success("SERIAL ID sequence reset to 1.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 9 — Reset Visit Logs
# =============================================================================

def reset_logs() -> None:
    """Delete all visit log entries and reset the SERIAL sequence."""
    clear_screen()
    header("RESET VISIT LOGS")

    warn("This will permanently delete ALL visit log entries.")
    print()

    if not confirm("Are you absolutely sure"):
        info("Reset cancelled.")
        pause()
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("DELETE FROM visit_logs")
        rows_deleted = cur.rowcount

        cur.execute("ALTER SEQUENCE visit_logs_id_seq RESTART WITH 1")

        conn.commit()
        cur.close()
        conn.close()

        success(f"Deleted {rows_deleted} visit log entry/entries.")
        success("SERIAL ID sequence reset to 1.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 10 — Reset Daily Statistics
# =============================================================================

def reset_statistics() -> None:
    """Delete all daily statistics rows."""
    clear_screen()
    header("RESET DAILY STATISTICS")

    warn("This will permanently delete ALL daily statistics.")
    print()

    if not confirm("Are you absolutely sure"):
        info("Reset cancelled.")
        pause()
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("DELETE FROM daily_statistics")
        rows_deleted = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        success(f"Deleted {rows_deleted} daily statistics row(s).")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 11 — Reset ENTIRE Database
# =============================================================================

def reset_database() -> None:
    """Nuke all tables and reset all SERIAL sequences."""
    clear_screen()
    header("RESET ENTIRE DATABASE")

    print(Fore.RED + Back.BLACK + Style.BRIGHT)
    print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("  !!!              DANGER — IRREVERSIBLE             !!!")
    print("  !!!                                                !!!")
    print("  !!!   This will DELETE every row in every table.  !!!")
    print("  !!!   customers, unknown_customers,               !!!")
    print("  !!!   visit_logs, daily_statistics                !!!")
    print("  !!!   All SERIAL sequences will be reset to 1.    !!!")
    print("  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(Style.RESET_ALL)

    if not confirm("Type Y to confirm complete database wipe"):
        info("Reset cancelled.")
        pause()
        return

    # Second confirmation — intentional friction
    print()
    double_check = input(
        Fore.RED + Style.BRIGHT
        + "  Type RESET to confirm: "
        + Style.RESET_ALL
    ).strip()

    if double_check != "RESET":
        info("Reset cancelled — confirmation text did not match.")
        pause()
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("DELETE FROM visit_logs")
        cur.execute("DELETE FROM daily_statistics")
        cur.execute("DELETE FROM unknown_customers")
        cur.execute("DELETE FROM customers")

        # Reset all SERIAL sequences
        cur.execute("ALTER SEQUENCE customers_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE unknown_customers_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE visit_logs_id_seq RESTART WITH 1")

        conn.commit()
        cur.close()
        conn.close()

        success("Entire database has been wiped.")
        success("All SERIAL ID sequences reset to 1.")

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 12 — Database Summary
# =============================================================================

def database_summary() -> None:
    """Print a concise summary of all table counts and today's stats."""
    clear_screen()
    header("DATABASE SUMMARY")

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        total_registered = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM unknown_customers")
        total_unknown = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM visit_logs")
        total_logs = cur.fetchone()[0]

        today = datetime.now().date().isoformat()
        cur.execute(
            """
            SELECT known_today, unknown_today, returning_unknown_today
            FROM daily_statistics
            WHERE stat_date = %s
            """,
            (today,)
        )
        today_row = cur.fetchone()
        known_today      = today_row[0] if today_row else 0
        unknown_today    = today_row[1] if today_row else 0
        returning_today  = today_row[2] if today_row else 0

        cur.execute("SELECT MIN(stat_date), MAX(stat_date) FROM daily_statistics")
        date_range = cur.fetchone()

        cur.close()
        conn.close()

        w = 30   # label column width

        print(Fore.CYAN + hr("─", 50))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Registered Customers':{w}}: " + Fore.GREEN  + str(total_registered))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Unknown Customers':{w}}: "    + Fore.RED    + str(total_unknown))
        print(Fore.CYAN + hr("─", 50))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Today — Known Visits':{w}}: " + Fore.GREEN  + str(known_today))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Today — Unknown Visits':{w}}: "+ Fore.RED    + str(unknown_today))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Today — Returning Unknown':{w}}: " + Fore.YELLOW + str(returning_today))
        print(Fore.CYAN + hr("─", 50))
        print(Fore.WHITE + Style.BRIGHT + f"  {'Total Visit Logs':{w}}: "     + Fore.BLUE   + str(total_logs))

        if date_range and date_range[0]:
            print(
                Fore.WHITE + Style.BRIGHT
                + f"  {'Statistics Range':{w}}: "
                + Fore.BLUE + f"{date_range[0]}  →  {date_range[1]}"
            )

        print(Fore.CYAN + hr("─", 50))

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 13 — Show Database Structure
# =============================================================================

def show_structure() -> None:
    """
    Query information_schema to show column details for every project table.
    Dynamically reads actual PostgreSQL schema — nothing is hardcoded.
    """
    clear_screen()
    header("DATABASE STRUCTURE")

    tables = ["customers", "unknown_customers", "visit_logs", "daily_statistics"]

    try:
        conn = get_connection()
        cur  = conn.cursor()

        for table in tables:
            cur.execute(
                """
                SELECT
                    c.column_name,
                    c.data_type,
                    CASE WHEN kcu.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_primary_key,
                    c.is_nullable,
                    c.column_default
                FROM information_schema.columns c
                LEFT JOIN information_schema.table_constraints tc
                    ON  tc.table_name   = c.table_name
                    AND tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = c.table_schema
                LEFT JOIN information_schema.key_column_usage kcu
                    ON  kcu.constraint_name = tc.constraint_name
                    AND kcu.column_name     = c.column_name
                WHERE c.table_name   = %s
                  AND c.table_schema = 'public'
                ORDER BY c.ordinal_position
                """,
                (table,)
            )
            columns = cur.fetchall()

            print(Fore.CYAN + Style.BRIGHT + f"\n  TABLE: {table.upper()}")
            print(Fore.CYAN + hr("─", 88))
            print(
                Fore.YELLOW + Style.BRIGHT
                + col("Column", 26)
                + col("Data Type", 24)
                + col("PK", 6)
                + col("Nullable", 12)
                + col("Default", 22)
            )
            print(Fore.CYAN + hr("─", 88))

            if not columns:
                print(Fore.RED + "  (table not found or no columns)")
                continue

            for (col_name, data_type, is_pk, nullable, default) in columns:
                pk_flag = Fore.GREEN + "YES" + Fore.WHITE if is_pk == "YES" else Fore.WHITE + "no"
                print(
                    Fore.WHITE
                    + col(col_name, 26)
                    + col(data_type, 24)
                    + pk_flag + " " * (6 - len("YES"))
                    + col(nullable, 12)
                    + col(default or "—", 22)
                )

        cur.close()
        conn.close()

    except Exception as exc:
        error(f"Database error: {exc}")

    pause()


# =============================================================================
# OPTION 14 — Export Database Report
# =============================================================================

def export_report() -> None:
    """
    Write a comprehensive plaintext report of the entire database to
    database_report.txt in the current working directory.
    """
    clear_screen()
    header("EXPORT DATABASE REPORT")

    filename = "database_report.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_connection()
        cur  = conn.cursor()

        lines: list[str] = []

        def section(title: str) -> None:
            lines.append("")
            lines.append("=" * 60)
            lines.append(f"  {title}")
            lines.append("=" * 60)

        def divider() -> None:
            lines.append("-" * 60)

        # --- Header ---
        lines.append("=" * 60)
        lines.append("  ITC FACE RECOGNITION — DATABASE REPORT")
        lines.append(f"  Generated: {timestamp}")
        lines.append("=" * 60)

        # --- Summary ---
        section("SUMMARY")

        cur.execute("SELECT COUNT(*) FROM customers")
        total_registered = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM unknown_customers")
        total_unknown = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM visit_logs")
        total_logs = cur.fetchone()[0]

        today = datetime.now().date().isoformat()
        cur.execute(
            "SELECT known_today, unknown_today, returning_unknown_today "
            "FROM daily_statistics WHERE stat_date = %s",
            (today,)
        )
        tr = cur.fetchone()

        lines.append(f"  Registered Customers     : {total_registered}")
        lines.append(f"  Unknown Customers        : {total_unknown}")
        lines.append(f"  Total Visit Logs         : {total_logs}")
        lines.append(f"  Today Known Visits       : {tr[0] if tr else 0}")
        lines.append(f"  Today Unknown Visits     : {tr[1] if tr else 0}")
        lines.append(f"  Today Returning Unknown  : {tr[2] if tr else 0}")

        # --- Registered Customers ---
        section("REGISTERED CUSTOMERS")
        cur.execute(
            "SELECT id, name, email, phone, visit_count, created_at, last_seen "
            "FROM customers ORDER BY id ASC"
        )
        rows = cur.fetchall()

        if rows:
            hdr = f"{'ID':<6}{'Name':<24}{'Email':<30}{'Phone':<18}{'Visits':<8}{'Created':<22}{'Last Seen':<22}"
            lines.append(hdr)
            divider()
            for (rid, name, email, phone, visits, created, last_seen) in rows:
                lines.append(
                    f"{str(rid):<6}"
                    f"{(name or ''):<24}"
                    f"{(email or '—'):<30}"
                    f"{(phone or '—'):<18}"
                    f"{str(visits):<8}"
                    f"{created.strftime('%Y-%m-%d %H:%M') if created else '—':<22}"
                    f"{last_seen.strftime('%Y-%m-%d %H:%M') if last_seen else '—':<22}"
                )
        else:
            lines.append("  (no registered customers)")

        # --- Unknown Customers ---
        section("UNKNOWN CUSTOMERS")
        cur.execute(
            "SELECT id, visit_count, first_seen, last_seen "
            "FROM unknown_customers ORDER BY id ASC"
        )
        rows = cur.fetchall()

        if rows:
            hdr = f"{'ID':<8}{'Visits':<10}{'First Seen':<26}{'Last Seen':<26}"
            lines.append(hdr)
            divider()
            for (rid, visits, first_seen, last_seen) in rows:
                lines.append(
                    f"{str(rid):<8}"
                    f"{str(visits):<10}"
                    f"{first_seen.strftime('%Y-%m-%d %H:%M:%S') if first_seen else '—':<26}"
                    f"{last_seen.strftime('%Y-%m-%d %H:%M:%S')  if last_seen  else '—':<26}"
                )
        else:
            lines.append("  (no unknown customers)")

        # --- Daily Statistics ---
        section("DAILY STATISTICS")
        cur.execute(
            "SELECT stat_date, known_today, unknown_today, returning_unknown_today "
            "FROM daily_statistics ORDER BY stat_date DESC"
        )
        rows = cur.fetchall()

        if rows:
            hdr = f"{'Date':<16}{'Known':<12}{'Unknown':<12}{'Returning':<14}"
            lines.append(hdr)
            divider()
            for (stat_date, known, unknown, returning) in rows:
                date_str = stat_date.isoformat() if hasattr(stat_date, "isoformat") else str(stat_date)
                lines.append(f"{date_str:<16}{str(known):<12}{str(unknown):<12}{str(returning):<14}")
        else:
            lines.append("  (no statistics recorded)")

        # --- Visit Logs (last 500) ---
        section("VISIT LOGS  (latest 500)")
        cur.execute(
            "SELECT id, customer_type, customer_id, visit_time "
            "FROM visit_logs ORDER BY id DESC LIMIT 500"
        )
        rows = cur.fetchall()

        if rows:
            hdr = f"{'ID':<8}{'Type':<22}{'Customer ID':<14}{'Visit Time':<24}"
            lines.append(hdr)
            divider()
            for (lid, ctype, cid, vtime) in rows:
                lines.append(
                    f"{str(lid):<8}"
                    f"{(ctype or ''):<22}"
                    f"{str(cid):<14}"
                    f"{vtime.strftime('%Y-%m-%d %H:%M:%S') if vtime else '—':<24}"
                )
        else:
            lines.append("  (no visit logs)")

        lines.append("")
        lines.append("=" * 60)
        lines.append("  END OF REPORT")
        lines.append("=" * 60)

        cur.close()
        conn.close()

        # Write to file
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        success(f"Report written to: {os.path.abspath(filename)}")

    except Exception as exc:
        error(f"Failed to generate report: {exc}")

    pause()


# =============================================================================
# MAIN — entry point and event loop
# =============================================================================

def main() -> None:
    """Main menu loop."""
    dispatch = {
        "1":  show_registered_customers,
        "2":  show_unknown_customers,
        "3":  show_visit_logs,
        "4":  show_daily_statistics,
        "5":  delete_customer,
        "6":  delete_unknown_customer,
        "7":  reset_registered,
        "8":  reset_unknown,
        "9":  reset_logs,
        "10": reset_statistics,
        "11": reset_database,
        "12": database_summary,
        "13": show_structure,
        "14": export_report,
    }

    while True:
        try:
            print_menu()
            choice = input(
                Fore.CYAN + Style.BRIGHT + "  Enter Choice: " + Style.RESET_ALL
            ).strip()

            if choice == "15":
                clear_screen()
                print()
                success("Goodbye.")
                print()
                sys.exit(0)

            if choice in dispatch:
                dispatch[choice]()
            else:
                clear_screen()
                print()
                warn(f"'{choice}' is not a valid option. Please enter 1–15.")
                pause()

        except KeyboardInterrupt:
            clear_screen()
            print()
            warn("Interrupted by user (Ctrl+C).")
            print()
            success("Goodbye.")
            print()
            sys.exit(0)

        except Exception as exc:
            error(f"Unexpected error: {exc}")
            pause()


# =============================================================================
if __name__ == "__main__":
    main()