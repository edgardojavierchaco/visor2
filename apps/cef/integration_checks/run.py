"""Sólo dos modalidades: offline y auditoría READ ONLY. No existe modo de escritura."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from safety import Blocked, offline_guard, safe_code, suppress_raw_output, verify_sources


def main():
    parser = argparse.ArgumentParser(description="CEF: offline o auditoría de solo lectura")
    parser.add_argument("--mode", choices=("offline", "audit"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--service", help="Servicio PostgreSQL RO explícito; sin contraseña en CLI")
    parser.add_argument("--expect-db")
    parser.add_argument("--expect-host")
    parser.add_argument("--expect-port", type=int, default=5432)
    parser.add_argument("--cycle", type=int)
    args = parser.parse_args()
    report = {"modalidad": args.mode, "integracion_postgresql": False, "resultados": []}
    try:
        verify_sources(Path(__file__).resolve().parent)
        if args.mode == "offline":
            with offline_guard(), suppress_raw_output():
                from quality_checks import security_checks, adapter_checks
                report["aislamiento"] = security_checks()
                report["contratos_adaptador"] = adapter_checks()
                from offline_support import run_offline
                report["resultados"] = run_offline(args.only)
        else:
            if args.only:
                raise Blocked("AUDITORIA_NO_ACEPTA_CASOS_OFFLINE")
            # No hay carga de settings ni fallback a la cuenta habitual de Django.
            with suppress_raw_output():
                from audit_readonly import audit
                report["resultados"] = audit(args)
    except (Exception, KeyboardInterrupt, SystemExit) as exc:
        report["resultados"].append({"codigo": "EJECUTOR", "resultado": "BLOCKED",
                                     "descripcion": safe_code(exc)})
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        try:
            with args.report.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(output + "\n")
        except OSError:
            print("BLOCKED: no se pudo crear un informe nuevo", file=sys.stderr)
            return 2
    results = [row["resultado"] for row in report["resultados"]]
    return 2 if "BLOCKED" in results else (1 if "FAIL" in results else 0)


if __name__ == "__main__":
    raise SystemExit(main())
