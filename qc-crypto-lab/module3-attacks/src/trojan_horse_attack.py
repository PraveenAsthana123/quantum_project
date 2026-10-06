"""
CUSTOMER DEMO PITCH — Trojan Horse Attack on QKD Devices
=========================================================
The Trojan Horse Attack (Vakhitov et al. 2001) is a side-channel attack where
Eve sends a BRIGHT PROBE PULSE into Bob's (or Alice's) measurement device.
The back-reflected light from Bob's optical components carries information about
his basis setting, leaking key information without touching the quantum channel.

Attack mechanism:
  1. Eve injects a bright (classical) light pulse into Bob's fiber input port.
  2. The pulse reflects off Bob's internal components (wave plates, beam splitters).
  3. The reflected pulse carries a different polarisation/phase depending on Bob's
     current basis setting (Z vs X).
  4. Eve measures the back-reflected pulse → learns Bob's basis → knows the key bit
     whenever Alice's basis matches Bob's (half the sifted key).

Countermeasures:
  - Optical isolators (30–60 dB isolation) block reflected light.
  - Watchdog detectors monitor for bright injection pulses.
  - Photon-number-resolving detectors at the input.

This is a REAL-WORLD attack; commercial QKD devices have been breached (Makarov group).

Audience: QKD hardware engineers, security architects, pen-testers.
Runtime: < 3 seconds (numpy only).
"""

import math
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 66
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def db_to_linear(db: float) -> float:
    return 10 ** (db / 10)


def linear_to_db(linear: float) -> float:
    if linear <= 0:
        return -math.inf
    return 10 * math.log10(linear)


# ---------------------------------------------------------------------------
# Trojan Horse Attack Model
# ---------------------------------------------------------------------------

# Bob's device typical reflection coefficients
COMPONENT_REFLECTIONS = {
    "Fiber connector (PC)":       -30,   # dB
    "Beam splitter":              -6,    # dB  (50% reflectance)
    "Wave plate (retarder)":      -20,   # dB
    "Faraday mirror":             -10,   # dB (used in plug-and-play systems)
    "Photodetector (APD)":        -25,   # dB
    "Total (worst-case cascade)": -3,    # dB  (dominant: beam splitter)
}

def trojan_horse_signal_chain(eve_probe_dBm: float,
                               isolation_dB:  float) -> dict:
    """
    Compute the power budget for a Trojan Horse attack.
    Eve injects probe at eve_probe_dBm.
    isolation_dB = insertion loss of optical isolator at input port (0 = no isolator).
    """
    # Probe arrives at Bob's internal components
    # Simplified: total reflection = -6 dB (beam splitter dominates)
    reflection_dB   = -6.0
    # Return path loss (same fiber, similar losses)
    return_loss_dB  = 3.0    # one-way fiber + connectors
    # Isolation blocks the return path
    effective_return_dB = reflection_dB - return_loss_dB - isolation_dB

    probe_power_mW     = 10 ** (eve_probe_dBm / 10)
    return_power_dBm   = eve_probe_dBm + effective_return_dB
    return_power_mW    = 10 ** (return_power_dBm / 10) if return_power_dBm > -100 else 0

    # Can Eve's detector see it? Typical APD sensitivity: -60 dBm minimum
    detectable = return_power_dBm > -60
    info_leak  = detectable   # simplified: if Eve can detect return, she gets basis info

    return {
        "probe_dBm":        eve_probe_dBm,
        "probe_mW":         probe_power_mW,
        "reflection_dB":    reflection_dB,
        "isolation_dB":     isolation_dB,
        "return_power_dBm": return_power_dBm,
        "return_power_mW":  return_power_mW,
        "detectable":       detectable,
        "info_leak":        info_leak,
    }


def basis_leakage_from_reflection(return_power_mW: float) -> dict:
    """
    Model information leakage from back-reflected light.
    If Eve can detect the reflection, she can distinguish Z vs X basis
    from the polarisation state of the reflected probe (basis-dependent reflectance).
    """
    apd_sensitivity_mW = 1e-6   # -60 dBm
    if return_power_mW < apd_sensitivity_mW:
        return {"basis_distinguishable": False, "info_bits_per_pulse": 0.0,
                "bob_key_fraction_leaked": 0.0}

    # If detectable: Eve can distinguish bases with some fidelity
    # Model: SNR proportional to return_power / sensitivity
    snr  = return_power_mW / apd_sensitivity_mW
    fid  = min(0.5 + 0.5 * (1 - 1 / (1 + snr)), 1.0)   # detection fidelity
    # Mutual information per pulse (binary asymmetric channel)
    p_err = 1 - fid
    h2   = (-p_err * math.log2(max(p_err, 1e-15)) -
             (1-p_err) * math.log2(max(1-p_err, 1e-15)))
    I_EB = max(0.0, 1.0 - h2)

    return {
        "basis_distinguishable":  fid > 0.6,
        "fidelity":               fid,
        "info_bits_per_pulse":    I_EB,
        "bob_key_fraction_leaked": I_EB / 2,   # half of sifted bits are Bob-match
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("TROJAN HORSE ATTACK ON QKD DEVICES")
    print("Purpose: Show bright-light injection, basis leakage, and countermeasures\n")

    # Bob's component reflections
    print_sep("Bob's Device: Internal Reflection Budget")
    print(f"  {'Component':<35}  {'Reflectance (dB)':>16}  {'Reflectance (linear)':>20}")
    print(f"  {'-'*35}  {'-'*16}  {'-'*20}")
    for comp, ref_dB in COMPONENT_REFLECTIONS.items():
        ref_lin = db_to_linear(ref_dB)
        print(f"  {comp:<35}  {ref_dB:>+16.1f}  {ref_lin:>20.6f}")

    print()

    # Signal chain: no isolator vs with isolator
    print_sep("Trojan Horse Signal Budget: Eve's Probe at +10 dBm (10 mW)")
    probe_dBm = 10.0   # 10 mW probe pulse

    print(f"  {'Isolation':>10}  {'Return (dBm)':>14}  {'Return (mW)':>12}  "
          f"{'Detectable':>11}  {'Info leaks?':>12}")
    print(f"  {'-'*10}  {'-'*14}  {'-'*12}  {'-'*11}  {'-'*12}")
    for iso_dB in [0, 15, 30, 45, 60, 80]:
        r = trojan_horse_signal_chain(probe_dBm, isolation_dB=iso_dB)
        print(f"  {iso_dB:>8} dB  {r['return_power_dBm']:>+12.1f}  "
              f"{r['return_power_mW']:>12.2e}  "
              f"{'YES' if r['detectable'] else 'no':>11}  "
              f"{'YES ← LEAK' if r['info_leak'] else 'Safe':>12}")

    print()

    # Information leakage detail
    print_sep("Basis Information Leakage Analysis (no isolator)")
    r_no_iso = trojan_horse_signal_chain(probe_dBm, isolation_dB=0)
    leak     = basis_leakage_from_reflection(r_no_iso["return_power_mW"])
    print(f"  Return power: {r_no_iso['return_power_mW']:.2e} mW  ({r_no_iso['return_power_dBm']:.1f} dBm)")
    print(f"  APD sensitivity threshold: 1e-6 mW (-60 dBm)")
    print(f"  SNR: {r_no_iso['return_power_mW'] / 1e-6:.0f}×")
    if leak["basis_distinguishable"]:
        print(f"  Basis distinguishable: YES")
        print(f"  Detection fidelity:    {leak['fidelity']:.4f}")
        print(f"  Info per pulse:        {leak['info_bits_per_pulse']:.4f} bits")
        print(f"  Key fraction leaked:   {leak['bob_key_fraction_leaked']:.4f}  "
              f"({leak['bob_key_fraction_leaked']*100:.1f}% of sifted key)")
    else:
        print(f"  Basis NOT distinguishable at this power level.")
    print()

    # Countermeasures table
    print_sep("Countermeasures")
    countermeasures = [
        ("Optical isolator (30 dB)",  30, "First line of defense; standard in commercial QKD"),
        ("Optical isolator (60 dB)",  60, "Military/telecom grade; blocks most probe powers"),
        ("Watchdog APD at input",      0, "Detects ANY bright pulse >threshold (~1 nW)"),
        ("Classical filter (bandpass)",0, "Blocks wavelengths outside QKD photon band"),
        ("Plug-and-play architecture", 0, "Bob sends probe back to Alice; Eve cannot inject"),
        ("Measurement-device-independent QKD", 0, "Eliminates all detector side-channels"),
    ]
    for name, iso, desc in countermeasures:
        if iso > 0:
            r = trojan_horse_signal_chain(probe_dBm, iso)
            status = "Leaks" if r["info_leak"] else "BLOCKED"
            print(f"  ✓ {name:<40}  {status}  — {desc}")
        else:
            print(f"  ✓ {name:<40}  (non-optical countermeasure)")
            print(f"    {desc}")

    print()
    print_sep("Real-World Incidents")
    print("""
  2010: Vadim Makarov's group (NTNU/Waterloo) demonstrated blinding attacks
        on commercial QKD systems (ID Quantique Clavis2, MagiQ QPN).
        Bright illumination blinded the SPDs; subsequent control pulses
        determined Bob's basis without triggering security checks.

  2011: Time-shift attack demonstrated on commercial QKD hardware.

  2016: Laser damage attack — Eve's bright pulse permanently damages Bob's SPD,
        changing its detection efficiency and leaking basis information.

  Industry response: All major commercial QKD vendors now include optical
        isolators (30–60 dB), watchdog detectors, and power monitoring.
        MDI-QKD (measurement-device-independent) architectures eliminate the
        entire attack surface by removing detectors from Alice and Bob's sites.
""")
    print_sep()


if __name__ == "__main__":
    main()
