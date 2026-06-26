"""
verify_deadlock_fix.py
======================
Runs 5 independent 180-tick simulations (different seeds) and reports:

  (a) Node zero-staff events: did any Hospital or School node hit 0 employees
      and stay there for more than 2 consecutive ticks?
  (b) SEIR visibility: are cumulative infected counts non-zero?
  (c) Hospital strain (slot-based): does hospital_strain record non-zero values
      during ticks where citizens were admitted? (Directly verifies the
      occupied_slots reset-timing fix.)
  (d) Money conservation: is the per-tick delta within a sane range?

Check (c) uses a single dedicated run where citizens are artificially forced
sick, giving reliable hospital admissions to confirm the metric captures them.
"""

import sys
from simulation.core.engine import SimulationEngine

SEEDS = [42, 7, 2024, 1337, 99]
TICKS = 180
PUBLIC_NODES = ("Hospital", "School")


def run_simulation(seed: int) -> dict:
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1_270_000_000_000.0,
        seed=seed,
    )

    zero_staff_runs: dict[str, int] = {}
    max_zero_staff_run: dict[str, int] = {}
    total_bailout_events: int = 0
    total_bailout_capital: float = 0.0

    seir_infected_totals = []
    hospital_op_cap_values = []
    money_deltas = []

    prev_money = (
        engine.government_capital
        + sum(n.capital for n in engine.nodes)
        + sum(c.bank_balance for c in engine.citizens if not c.is_dead)
        - sum(c.debt for c in engine.citizens if not c.is_dead)
    )

    for tick in range(1, TICKS + 1):
        engine.step()

        for node in engine.nodes:
            if node.node_type not in PUBLIC_NODES:
                continue
            nid = node.node_id
            if len(node.employees) == 0:
                zero_staff_runs[nid] = zero_staff_runs.get(nid, 0) + 1
            else:
                run = zero_staff_runs.pop(nid, 0)
                if run > 0:
                    max_zero_staff_run[nid] = max(
                        max_zero_staff_run.get(nid, 0), run
                    )

        if engine.tick_public_bailout_total > 0:
            total_bailout_events += 1
            total_bailout_capital += engine.tick_public_bailout_total

        latest = engine.history[-1]
        seir_infected_totals.append(latest.get("seir_infected", 0))

        hosp = engine.get_node_by_id("hosp_city")
        if hosp:
            hospital_op_cap_values.append(hosp.operational_capacity)

        cur_money = (
            engine.government_capital
            + sum(n.capital for n in engine.nodes)
            + sum(c.bank_balance for c in engine.citizens if not c.is_dead)
            - sum(c.debt for c in engine.citizens if not c.is_dead)
        )
        money_deltas.append(cur_money - prev_money)
        prev_money = cur_money

    for nid, run in zero_staff_runs.items():
        max_zero_staff_run[nid] = max(max_zero_staff_run.get(nid, 0), run)

    return {
        "seed": seed,
        "max_zero_staff_run": max_zero_staff_run,
        "any_deadlock": any(v > 2 for v in max_zero_staff_run.values()),
        "total_seir_infected": sum(seir_infected_totals),
        "peak_seir_infected": max(seir_infected_totals),
        "hospital_op_cap_min": min(hospital_op_cap_values) if hospital_op_cap_values else 0,
        "hospital_op_cap_max": max(hospital_op_cap_values) if hospital_op_cap_values else 0,
        "hospital_op_cap_always_positive": all(v > 0 for v in hospital_op_cap_values),
        "total_bailout_events": total_bailout_events,
        "total_bailout_capital": total_bailout_capital,
        "money_delta_min": min(money_deltas),
        "money_delta_max": max(money_deltas),
    }


def verify_hospital_strain_metric() -> dict:
    """
    Dedicated 20-tick run with forced sick population to directly verify that
    hospital_strain in recorded metrics is non-zero when patients are admitted.
    """
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1_270_000_000_000.0,
        seed=42,
    )
    engine.policies["healthcare_subsidy"] = 1.0
    engine.policies["free_emergency_care"] = True

    nonzero_ticks = 0
    for tick in range(1, 21):
        # Force a reliable sick cohort each tick
        for c in engine.citizens[:20]:
            if not c.is_dead:
                c.health = 20.0
                c.seir_state = "I"
        engine.step()
        strain = engine.history[-1].get("hospital_strain", 0.0)
        if strain > 0.0:
            nonzero_ticks += 1

    return {
        "nonzero_strain_ticks": nonzero_ticks,
        "total_ticks": 20,
        "pass": nonzero_ticks == 20,
    }


def main():
    print("=" * 70)
    print("NODE DEADLOCK FIX + HOSPITAL_STRAIN FIX VERIFICATION")
    print("5 seeds × 180 ticks  +  1 dedicated strain measurement run")
    print("=" * 70)

    # ── Check (c): hospital_strain metric fix ────────────────────────────────
    print("\n▶  Verifying hospital_strain metric (20-tick forced-sick run)...")
    strain_result = verify_hospital_strain_metric()
    strain_pass = strain_result["pass"]
    print(f"   hospital_strain non-zero in "
          f"{strain_result['nonzero_strain_ticks']} / {strain_result['total_ticks']} ticks")
    print(f"   {'✅ PASS — slot-based strain metric now correctly captures admissions'
              if strain_pass else '❌ FAIL — hospital_strain still reads 0'}")

    # ── Checks (a), (b), (d): deadlock + SEIR + conservation ────────────────
    all_results = []
    for seed in SEEDS:
        print(f"\n▶  Running seed={seed} ({TICKS} ticks)...", flush=True)
        result = run_simulation(seed)
        all_results.append(result)

        print(f"   (a) Max consecutive 0-staff ticks per public node:")
        if result["max_zero_staff_run"]:
            for nid, run in result["max_zero_staff_run"].items():
                tag = "❌ DEADLOCK" if run > 2 else "✅ OK"
                print(f"       {nid}: {run} ticks   {tag}")
        else:
            print("       ✅ No 0-staff events recorded")

        print(f"   (b) SEIR: total={result['total_seir_infected']:,}  "
              f"peak={result['peak_seir_infected']}")
        seir_ok = result["total_seir_infected"] > 0
        print(f"       {'✅ SEIR non-zero' if seir_ok else '❌ SEIR zero'}")

        print(f"   (c-employee) Hospital op_capacity: "
              f"min={result['hospital_op_cap_min']}  max={result['hospital_op_cap_max']}")
        op_ok = result["hospital_op_cap_always_positive"]
        print(f"       {'✅ Always > 0' if op_ok else '❌ Hit 0 at some point'}")

        print(f"   (d) Money delta: "
              f"[{result['money_delta_min']:,.1f}, {result['money_delta_max']:,.1f}]  "
              f"| Bailout events: {result['total_bailout_events']} "
              f"(${result['total_bailout_capital']:,.0f})")
        money_ok = result["money_delta_min"] > -1e9
        print(f"       {'✅ Conservation OK' if money_ok else '❌ Suspicious negative delta'}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    deadlock_any    = any(r["any_deadlock"] for r in all_results)
    seir_any_zero   = any(r["total_seir_infected"] == 0 for r in all_results)
    op_cap_any_zero = any(not r["hospital_op_cap_always_positive"] for r in all_results)
    money_any_bad   = any(r["money_delta_min"] < -1e9 for r in all_results)

    print(f"  (a) No deadlock (>2 consecutive 0-staff ticks):     "
          f"{'✅ PASS' if not deadlock_any else '❌ FAIL'}")
    print(f"  (b) SEIR infections visible across all seeds:        "
          f"{'✅ PASS' if not seir_any_zero else '❌ FAIL'}")
    print(f"  (c) hospital_strain non-zero when patients admitted: "
          f"{'✅ PASS' if strain_pass else '❌ FAIL'}")
    print(f"  (d) Money conservation delta within sane range:      "
          f"{'✅ PASS' if not money_any_bad else '❌ FAIL'}")

    if deadlock_any or seir_any_zero or not strain_pass or money_any_bad:
        print("\n❌  One or more checks FAILED.")
        sys.exit(1)
    else:
        print("\n✅  All checks PASSED.")


if __name__ == "__main__":
    main()
