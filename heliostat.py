import math
import time
import datetime
import serial
from pysolar.solar import get_altitude, get_azimuth


# ============================================================
# KONFIGURACJA
# ============================================================

PORT = "/dev/cu.usbmodem1201"
BAUD = 115200

# Lokalizacja heliostatu
LATITUDE = 50.0647
LONGITUDE = 19.9450

# Cel:
# azymuyt i wysokość
TARGET_AZIMUTH_DEG = 275.0
TARGET_ALTITUDE_DEG = 37.5

# Godziny pracy w NORMAL
START_HOUR = 8
END_HOUR = 13

# Co ile sekund poprawka w NORMAL
UPDATE_SECONDS = 20

# Minimalna wysokość Słońca, żeby w ogóle śledzić
MIN_SUN_ALTITUDE = 3.0


# ============================================================
# KALIBRACJA SERW
# ============================================================

# ------------------------
# GŁOWA / TILT / PIN 3
# ------------------------
TILT_MIN_US = 430
TILT_MAX_US = 2500

# 2050 us = lustro na płasko
TILT_ZERO_US = 2050

# z pomiarów:
# ok. 21.9 us / 1 stopień pochylenia lustra
TILT_US_PER_DEG = 21.9


# ------------------------
# PODSTAWA / BASE / PIN 6
# ------------------------
BASE_MIN_US = 430
BASE_MAX_US = 2400

# 1415 us = środek
BASE_ZERO_US = 1415

# przy 1415 us baza ustawiona na azymut 220°
BASE_ZERO_AZIMUTH = 220.0

# około 180° między 430 a 2400 us
BASE_US_PER_DEG = 10.94

# kierunek:
# większe us = mniejszy azymut
# mniejsze us = większy azymut


# ============================================================
# POMOCNICZE - MATEMATYKA
# ============================================================

def normalize(v):
    x, y, z = v
    length = math.sqrt(x * x + y * y + z * z)

    if length == 0:
        raise ValueError("Wektor ma długość zero.")

    return (x / length, y / length, z / length)


def clamp(value, low, high):
    return max(low, min(high, value))


def wrap_to_180(angle_deg):
    return (angle_deg + 180.0) % 360.0 - 180.0


def direction_from_azimuth_altitude(azimuth_deg, altitude_deg):
    """
    Układ:
    X = wschód
    Y = północ
    Z = góra
    """
    az = math.radians(azimuth_deg)
    alt = math.radians(altitude_deg)

    x = math.cos(alt) * math.sin(az)
    y = math.cos(alt) * math.cos(az)
    z = math.sin(alt)

    return normalize((x, y, z))


def vector_to_azimuth_altitude(v):
    x, y, z = normalize(v)

    azimuth = math.degrees(math.atan2(x, y)) % 360.0
    altitude = math.degrees(math.asin(z))

    return azimuth, altitude


# ============================================================
# PRZELICZENIA SERW
# ============================================================

def mirror_tilt_deg_to_us(tilt_deg):
    """
    tilt_deg = pochylenie lustra względem pozycji 'na płasko'

    0°   -> lustro na płasko
    25°  -> odpowiadało ok. 1500 us
    48°  -> odpowiadało ok. 1000 us
    """
    pulse = round(TILT_ZERO_US - tilt_deg * TILT_US_PER_DEG)
    pulse = clamp(pulse, TILT_MIN_US, TILT_MAX_US)
    return pulse


def azimuth_deg_to_base_us(azimuth_deg):
    """
    BASE_ZERO_US = 1415 us odpowiada azymutowi 220°.

    Z kalibracji:
    większe us -> mniejszy azymut
    mniejsze us -> większy azymut
    """
    diff_deg = wrap_to_180(azimuth_deg - BASE_ZERO_AZIMUTH)

    pulse = round(BASE_ZERO_US - diff_deg * BASE_US_PER_DEG)
    pulse = clamp(pulse, BASE_MIN_US, BASE_MAX_US)
    return pulse


# ============================================================
# GEOMETRIA HELIOSTATU
# ============================================================

TARGET_VECTOR = direction_from_azimuth_altitude(
    TARGET_AZIMUTH_DEG,
    TARGET_ALTITUDE_DEG
)


def compute_solution_for_local_datetime(local_dt):
    """
    Zwraca:
    - pozycję Słońca,
    - wymaganą normalną lustra,
    - wymagane pochylenie lustra,
    - impulsy dla obu serw.
    """
    utc_dt = local_dt.astimezone(datetime.timezone.utc)

    sun_alt = get_altitude(LATITUDE, LONGITUDE, utc_dt)
    sun_az = get_azimuth(LATITUDE, LONGITUDE, utc_dt) % 360.0

    if sun_alt < MIN_SUN_ALTITUDE:
        return {
            "ok": False,
            "reason": "Słońce zbyt nisko nad horyzontem.",
            "sun_az": sun_az,
            "sun_alt": sun_alt
        }

    sun_vector = direction_from_azimuth_altitude(sun_az, sun_alt)

    # Prawo odbicia:
    # normalna lustra = znormalizowana suma kierunku do Słońca i do celu
    normal_vector = normalize((
        sun_vector[0] + TARGET_VECTOR[0],
        sun_vector[1] + TARGET_VECTOR[1],
        sun_vector[2] + TARGET_VECTOR[2]
    ))

    normal_az, normal_alt = vector_to_azimuth_altitude(normal_vector)

    # Lustro "na płasko" = normalna pionowo w górę = 90° elewacji
    # Stąd:
    mirror_tilt_deg = 90.0 - normal_alt

    base_us = azimuth_deg_to_base_us(normal_az)
    tilt_us = mirror_tilt_deg_to_us(mirror_tilt_deg)

    return {
        "ok": True,
        "sun_az": sun_az,
        "sun_alt": sun_alt,
        "normal_az": normal_az,
        "normal_alt": normal_alt,
        "mirror_tilt_deg": mirror_tilt_deg,
        "base_us": base_us,
        "tilt_us": tilt_us
    }


# ============================================================
# KOMUNIKACJA Z ARDUINO
# ============================================================

print("Łączenie z Arduino...")

arduino = serial.Serial(PORT, BAUD, timeout=1)

# Arduino resetuje się po otwarciu portu
time.sleep(2)

print("Połączono z Arduino.")


def read_arduino_responses(wait=0.25):
    time.sleep(wait)

    responses = []

    while arduino.in_waiting:
        line = arduino.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if line:
            responses.append(line)

    return responses


def send_raw(command, show=True):
    if show:
        print(f">>> {command}")

    arduino.write((command + "\n").encode("utf-8"))

    responses = read_arduino_responses()

    for line in responses:
        print(f"Arduino: {line}")


def send_zero():
    send_raw("ZERO")


def send_test():
    send_raw("TEST")


def send_status():
    send_raw("STATUS")


def send_normal_position(base_us, tilt_us):
    send_raw("NORMAL")
    send_raw(f"SET {base_us} {tilt_us}")


# ============================================================
# WYDRUK WYNIKÓW
# ============================================================

def print_solution(label, local_dt, sol):
    print()
    print("==========================================")
    print(label)
    print("Czas:", local_dt.strftime("%Y-%m-%d %H:%M:%S"))
    print("==========================================")

    if not sol["ok"]:
        print(f"Słońce: az={sol['sun_az']:.2f}°  alt={sol['sun_alt']:.2f}°")
        print("Brak śledzenia:", sol["reason"])
        return

    print(f"Słońce:           az={sol['sun_az']:.2f}°   alt={sol['sun_alt']:.2f}°")
    print(f"Normalna lustra:  az={sol['normal_az']:.2f}°   alt={sol['normal_alt']:.2f}°")
    print(f"Pochylenie lustra od płasko: {sol['mirror_tilt_deg']:.2f}°")
    print(f"BASE -> {sol['base_us']} us")
    print(f"TILT -> {sol['tilt_us']} us")


# ============================================================
# TRYBY
# ============================================================

def run_zero_mode():
    print()
    print("TRYB ZERO")
    send_zero()


def run_test_mode():
    print()
    print("TRYB TEST")
    print("Możesz ręcznie wpisywać:")
    print("  b 1600")
    print("  t 1500")
    print("  zero")
    print("  status")
    print("  back")


def run_simulation_for_time(hour, minute):
    now_local = datetime.datetime.now().astimezone()

    sim_dt = now_local.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    sol = compute_solution_for_local_datetime(sim_dt)

    print_solution("SYMULACJA", sim_dt, sol)

    if sol["ok"]:
        send_normal_position(sol["base_us"], sol["tilt_us"])
    else:
        send_zero()


def run_normal_loop():
    print()
    print("TRYB NORMAL")
    print("Automatyczne śledzenie między 08:00 a 13:00.")
    print("Naciśnij Ctrl+C, aby wrócić do menu.")
    print()

    try:
        while True:
            now_local = datetime.datetime.now().astimezone()
            hour_float = now_local.hour + now_local.minute / 60.0

            if START_HOUR <= hour_float < END_HOUR:
                sol = compute_solution_for_local_datetime(now_local)

                print_solution("NORMAL", now_local, sol)

                if sol["ok"]:
                    send_normal_position(sol["base_us"], sol["tilt_us"])
                else:
                    send_zero()
            else:
                print()
                print("Poza godzinami pracy heliostatu.")
                print("Wracam do ZERO.")
                send_zero()

            time.sleep(UPDATE_SECONDS)

    except KeyboardInterrupt:
        print()
        print("Wyjście z NORMAL - powrót do menu.")


# ============================================================
# HELP
# ============================================================

def print_help():
    print()
    print("DOSTĘPNE KOMENDY:")
    print()
    print("  normal")
    print("      uruchamia automatyczne śledzenie w czasie rzeczywistym")
    print()
    print("  test")
    print("      przełącza Arduino do ręcznego trybu TEST")
    print("      potem możesz wpisywać np. b 1600 albo t 1500")
    print()
    print("  zero")
    print("      ustawia bezpieczną pozycję ZERO")
    print()
    print("  sim 08:00")
    print("  sim 10:30")
    print("      symuluje wybraną godzinę i ustawia heliostat")
    print()
    print("  status")
    print("      pokazuje stan Arduino")
    print()
    print("  b 1600")
    print("  t 1500")
    print("      ręczne sterowanie tylko w TEST")
    print()
    print("  help")
    print("      pokazuje tę pomoc")
    print()
    print("  quit")
    print("      kończy program")
    print()


# ============================================================
# START
# ============================================================

print()
print("HELIOSTAT - PANEL STEROWANIA")
print_help()
send_status()


# ============================================================
# GŁÓWNA PĘTLA KOMEND
# ============================================================

try:
    while True:
        command = input("\nPolecenie: ").strip()

        if not command:
            continue

        lower = command.lower()

        # -------------------------------------
        # QUIT
        # -------------------------------------
        if lower == "quit":
            print("Kończę program.")
            break

        # -------------------------------------
        # HELP
        # -------------------------------------
        elif lower == "help":
            print_help()

        # -------------------------------------
        # STATUS
        # -------------------------------------
        elif lower == "status":
            send_status()

        # -------------------------------------
        # ZERO
        # -------------------------------------
        elif lower == "zero":
            run_zero_mode()

        # -------------------------------------
        # TEST
        # -------------------------------------
        elif lower == "test":
            send_test()
            run_test_mode()

        # -------------------------------------
        # NORMAL
        # -------------------------------------
        elif lower == "normal":
            run_normal_loop()

        # -------------------------------------
        # SIM HH:MM
        # -------------------------------------
        elif lower.startswith("sim "):
            try:
                time_part = command[4:].strip()
                hh_str, mm_str = time_part.split(":")
                hh = int(hh_str)
                mm = int(mm_str)

                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                    raise ValueError

                run_simulation_for_time(hh, mm)

            except ValueError:
                print("Błędny format. Użyj np. sim 08:00")

        # -------------------------------------
        # RĘCZNE B / T
        # -------------------------------------
        elif lower.startswith("b "):
            send_raw(command.upper())

        elif lower.startswith("t "):
            send_raw(command.upper())

        else:
            print("Nieznane polecenie. Wpisz help.")

finally:
    arduino.close()
    print("Port szeregowy zamknięty.")

# github test add line