#!/usr/bin/env python3
"""Container-only acceptance driver. Expected values come from the immutable shared fixture."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import signal
from datetime import datetime, timezone

FLAGS = {
    "run_correct": False, "fill_gaps_from_ref": False, "skip_annotation_transfer": False,
    "skip_merge": False, "liftoff_copies": True, "fix_generic_names": True,
    "fix_reference_gff": True, "fix_vendor_gff": True, "merge_novel_only": False,
    "reorient_assembly": None,
}
TIERS = ("single", "low", "medium", "high", "unlabelled")
ROUTES = ("full", "annotation_transfer_only")
CONTRACT_HASH = "2a00165b10f57ba9812aac12debb47abb35c2c716b10d48858ad4b3c194ff398"
FIXTURE_HASH = "32a1105d46420837bb1fbe148c9b4e5d095213f5d2a2856c43ba09448d83a8ab"
SELECTOR = "ERROR: --workflow must be 'full' or 'annotation_transfer_only'; received '<value>'."

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")

def render(value):
    if isinstance(value, str):
        return value.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

def cli_values(values):
    return ["--" + key + "=" + (value if isinstance(value, str) else json.dumps(value, separators=(",", ":")))
            for key, value in values.items()]

def expected_tiers(cap):
    # Independent integer oracle for precedence/detection; R rows use literal fixture triples.
    c, m, t = cap
    def tier(d, cf, mf, tf):
        return [min(c, max(cf, (c + d - 1) // d)),
                min(m, max(mf, max(1, (m // 1048576 + d - 1) // d) * 1048576)),
                min(t, max(tf, (t + d - 1) // d))]
    return dict(single=[1, min(m, 2147483648), min(t, 3600000)],
                low=tier(4, 1, 1073741824, 3600000),
                medium=tier(2, 2, 2147483648, 14400000),
                high=list(cap), unlabelled=list(cap))

class Driver:
    def __init__(self, args):
        self.args = args
        self.repo, self.phase = Path(args.repo), Path(args.phase)
        self.vectors = json.loads((self.repo / "tests/integration/resource_vectors.json").read_text())
        self.resources = {row["id"]: row for row in self.vectors["resource_cases"]}
        self.caps = self.resources[self.vectors["expansion_rules"]["entry_valid_resource_ref"]]["input"]
        assert hashlib.sha256((self.repo / "tests/integration/resource_vectors.json").read_bytes()).hexdigest() == FIXTURE_HASH
        assert hashlib.sha256((self.repo / "docs/plans/2026-10-04-resource-contract.md").read_bytes()).hexdigest() == CONTRACT_HASH
        self.inventory = []
        self.results = []
        self.coverage = []
        self.safety = self.repo / "tests/parser_resources/probe.config"
        self.fixture = self.repo / "tests/fixtures/parser_resources"
        self.templates = dict(self.vectors["diagnostic_templates"], E_WORKFLOW=SELECTOR)
        self.planning = True
        self.prepare_inventory()
        self.planning = False

    def prepare_inventory(self):
        self.register("engine-version")
        mode = self.args.mode
        if mode in ("entry-parameters", "previews", "legacy-entry"):
            getattr(self, mode.replace("-", "_"))()
        elif mode == "static":
            self.register("lint")
        elif mode == "unsupported":
            self.register("floor", expected="nonzero")
        elif mode == "fractions":
            self.fractions()
        elif mode == "contract":
            for profile in ("standard", "docker", "conda", "singularity", "singularity_conda", "test", "test,docker", "docker,test"):
                self.register("config-" + profile.replace(",", "-"))
            for row in self.vectors["resource_cases"]:
                if self.args.parser != "unset" or row["id"] in ("R02", "R03"):
                    for transport in row["transports"]:
                        self.register(row["id"] + "-" + transport, transport)
            for row in self.vectors["precedence_cases"]:
                if self.args.parser != "unset" or row["id"] == "P06":
                    self.register(row["id"], "cli")
            cases = ["L01", "D01-raw", "D01"] if self.args.parser == "unset" else [
                "L01", "L02", "L03", "D01-raw", "D01", "D02-raw", "D02", "D03-raw", "D03", "D04"]
            for case in cases:
                self.register(case)
            if self.args.parser != "unset":
                for transport in ("yaml", "cli"):
                    case = "H-" + transport.upper()
                    self.register(case, transport)
                    for row in self.helper_rows(transport):
                        self.coverage_row(row, case, transport, "helper", row.get("diagnostic", row.get("expected")))
        elif mode == "docker-rename":
            self.register("RENAME")
        elif mode in ("integration-resources", "scaffolding-preview", "scaffolding-modules", "scaffolding-smoke"):
            getattr(self, mode.replace("-", "_"))()
        elif mode == "annotation-smoke":
            self.register("ANNOTATION")
            for flag, value in dict(reorient_assembly=False, fix_reference_gff=False, fix_vendor_gff=False,
                    liftoff_copies=False, merge_novel_only=True, skip_merge=False, fix_generic_names=True).items():
                self.coverage_row(dict(id="CONSUMER-" + flag, parameter=flag, organism="fungal"),
                    "ANNOTATION", "cli", "consumer", value)
            for transport, tag in (("yaml", "null"), ("cli", "zero"), ("yaml", "zero"), ("cli", "positive"), ("yaml", "positive")):
                case = "COMMANDS-" + transport + "-" + tag
                self.register(case, transport)
                for flag, value in {"merge_novel_only":False, "max_gene_length_bp":{"null":None, "zero":0, "positive":10000}[tag]}.items():
                    self.coverage_row(dict(id="CONSUMER-" + flag, parameter=flag), case, transport, "consumer", value)
        self.write_tables()

    def write_tables(self):
        for name, rows, cols in (
            ("case-inventory.tsv", self.inventory, ["case", "transport", "expected", "artifact", "outcome"]),
            ("results.tsv", self.results, ["contract", "case", "engine", "parser", "transport", "tier", "attempt", "cpus", "memory_bytes", "time_ms", "expectation", "status"]),
            ("parameter-coverage.tsv", self.coverage, ["case_id", "flag_dimension", "organism", "parser", "transport", "layer", "invocation_id", "expected", "artifact", "outcome"]),
        ):
            with (self.phase / name).open("w") as handle:
                writer = csv.DictWriter(handle, fieldnames=cols, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)

    def register(self, case, transport="", expected="zero"):
        existing = next((row for row in self.inventory if row["case"] == case), None)
        if existing:
            assert existing["expected"] == expected
            return existing
        row = dict(case=case, transport=transport, expected=expected, artifact=str(self.phase / case), outcome="PENDING")
        self.inventory.append(row)
        self.write_tables()
        return row

    def coverage_row(self, row, invocation, transport, layer, expected):
        if any(r["case_id"] == row["id"] and r["flag_dimension"] == row.get("parameter", "")
               and r["invocation_id"] == invocation for r in self.coverage):
            return
        self.coverage.append(dict(case_id=row["id"], flag_dimension=row.get("parameter", ""),
            organism=row.get("organism", ""), parser=self.args.parser, transport=transport, layer=layer,
            invocation_id=invocation, expected=json.dumps(expected), artifact=str(self.phase / invocation), outcome="PENDING"))

    def case_dir(self, case):
        path = self.phase / case
        path.mkdir()
        (path / "RUN.txt").write_text((self.phase / "RUN.txt").read_text() +
            "\nstarted_case: " + datetime.now(timezone.utc).isoformat() + "\npurpose_case: " + case + "\n")
        for name in ("home", "nxf-home", "cache", "temp", "work"):
            (path / name).mkdir()
        return path

    def run(self, case, args, transport="", expected="zero", env=None, setup=None, configs=None):
        row = next((x for x in self.inventory if x["case"] == case), None)
        if row is None:
            row = self.register(case, transport, expected)
        path = self.case_dir(case)
        if setup:
            setup(path)
        command = ["nextflow", "-log", str(path / ".nextflow.log")]
        for config in configs or []:
            command += ["-c", str(config)]
        command += [str(x).replace("{CASE}", str(path)) for x in args]
        local_env = os.environ.copy()
        local_env.update(HOME=str(path / "home"), NXF_HOME=str(path / "nxf-home"),
                         NXF_CACHE_DIR=str(path / "cache"), NXF_TEMP=str(path / "temp"), TMPDIR=str(path / "temp"),
                         NXF_ANSI_LOG="false")
        if self.args.parser == "unset":
            local_env.pop("NXF_SYNTAX_PARSER", None)
        else:
            local_env["NXF_SYNTAX_PARSER"] = self.args.parser
        local_env.update(env or {})
        (path / "command.txt").write_text(shlex.join(command) + "\n")
        dump(path / "environment.json", {k: v for k, v in local_env.items() if k.startswith("NXF_") or k in ("HOME", "TMPDIR")})
        with (path / "output.log").open("w") as handle:
            process = subprocess.Popen(command, cwd=path, env=local_env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=1200 if case.startswith('FULL-') else 600)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                # Only containers whose working directory belongs to this case.
                stopped = []
                if Path('/var/run/docker.sock').exists():
                    active = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
                    for container in active:
                        info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
                        if info['Config']['WorkingDir'].startswith(str(path / 'work') + '/'):
                            stopped.append(info)
                            subprocess.run(['docker', 'stop', '-t', '10', container], check=True)
                    dump(path / 'timeout-containers.json', stopped)
                (path / 'exit-code.txt').write_text('124\n')
                row['outcome'] = 'TIMEOUT'
                self.write_tables()
                raise AssertionError('Timed out: ' + case)
        result = subprocess.CompletedProcess(command, code)
        (path / "exit-code.txt").write_text(str(result.returncode) + "\n")
        output = (path / "output.log").read_text()
        if code in (137, -9) or re.search(r'out of memory|OOMKilled|exit status.*137|exit code.*137', output, re.I):
            row['outcome'] = 'OOM_OR_SUSPECTED_OOM'
            self.write_tables()
            raise AssertionError('Stop/report OOM or suspected OOM: ' + case)
        if (result.returncode == 0) != (expected == "zero"):
            row["outcome"] = "FAIL"
            self.write_tables()
            raise AssertionError("%s: exit %s, expected %s\n%s" % (case, result.returncode, expected, output[-5000:]))
        row["outcome"] = "EXIT_OK"
        self.write_tables()
        return path, output

    def passed(self, case):
        next(x for x in self.inventory if x["case"] == case)["outcome"] = "PASS"
        for row in self.coverage:
            if row["invocation_id"] == case:
                row["outcome"] = "PASS"
        self.write_tables()
        print("PASS", case, flush=True)

    def no_tasks(self, path):
        log = (path / ".nextflow.log").read_text() if (path / ".nextflow.log").exists() else ""
        assert not re.search(r"(Submitted process|Cached process|TaskHandler\[|Launching process)", log), str(path)
        assert not list((path / "work").rglob(".command.sh")), str(path)
        trace = path / "trace.tsv"
        if trace.exists():
            assert len(trace.read_text().splitlines()) <= 1

    def diagnostic(self, text, template, value=None, transport="yaml", parameter=None):
        template = self.templates.get(template, template).replace("<name>", parameter or "")
        if transport == "yaml":
            expected = template.replace("<value>", render(value))
            assert expected in text, (expected, text[-3000:])
        else:
            prefix, suffix = template.split("<value>")
            assert re.search(re.escape(prefix) + r"(?:\\.|[^'\r\n])*" + re.escape(suffix), text), (template, text[-3000:])

    def trace_config(self, path):
        (path / "trace-resources.config").write_text(
            "trace.enabled = true\ntrace.raw = true\ntrace.file = " + repr(str(path / "trace.tsv")) +
            "\ntrace.fields = 'task_id,hash,name,status,exit,cpus,memory,time'\n")

    def resource(self, case, inputs=None, transport="cli", expected=None, mode="execute", extra_configs=None, extra_args=None, env=None):
        values = dict(inputs or {})
        def setup(path):
            self.trace_config(path)
            dump(path / "effective-inputs.json", values)
            if transport == "yaml":
                dump(path / "params.yaml", values)  # JSON is a lossless YAML subset.
        args = ["run", self.repo / "tests/integration/resource_probe.nf",
                "-cache", "false", "-work-dir", "{CASE}/work", "--outdir={CASE}/results", "--probe_mode=" + mode]
        if transport == "yaml":
            args += ["-params-file", "{CASE}/params.yaml"]
        else:
            args += cli_values(values)
        args += extra_args or []
        path, output = self.run(case, args, transport, setup=setup, env=env,
            configs=[self.repo / "nextflow.config"] + list(extra_configs or []) + [self.safety, self.phase / case / "trace-resources.config"])
        records = []
        for record_path in (path / "work").rglob("resolved.json"):
            record = json.loads(record_path.read_text())
            record["work_hash"] = record_path.parent.parent.name + "/" + record_path.parent.name[:6]
            records.append(record)
        records.sort(key=lambda r: (r["tier"], r["attempt"]))
        dump(path / "observed.json", records)
        dump(path / "expected.json", expected)
        assert len(records) == (2 if mode == "retry" else len(expected)), (case, records)
        assert set(r["tier"] for r in records) == set(expected), (case, records)
        for record in records:
            triple = [record[k] for k in ("cpus", "memory_bytes", "time_ms")]
            assert triple == expected[record["tier"]], (case, record, expected)
            self.results.append(dict(contract="cc-resource-v1", case=case, engine=self.args.engine, parser=self.args.parser,
                transport=transport, tier=record["tier"], attempt=record["attempt"], cpus=triple[0],
                memory_bytes=triple[1], time_ms=triple[2], expectation=json.dumps(expected[record["tier"]]), status="PASS"))
        if mode == "retry":
            assert sorted(r["attempt"] for r in records) == [1, 2]
        with (path / "trace.tsv").open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            assert reader.fieldnames == ["task_id", "hash", "name", "status", "exit", "cpus", "memory", "time"]
            trace = list(reader)
        assert len(trace) == len(records), (case, trace, records)
        for item in trace:
            matches = [r for r in records if r["work_hash"] == item["hash"]]
            assert len(matches) == 1, (item, records)
            r = matches[0]
            r["task_id"], r["name"] = item["task_id"], item["name"]
            assert [int(item[k]) for k in ("cpus", "memory", "time")] == [r[k] for k in ("cpus", "memory_bytes", "time_ms")]
            assert item["status"] in (["FAILED", "COMPLETED"] if mode == "retry" else ["COMPLETED"])
        dump(path / "observed.json", records)
        self.passed(case)

    def static(self):
        path, output = self.run("lint", ["lint", self.repo])
        assert not re.search(r"\b[1-9][0-9]* errors\b", output), output
        self.no_tasks(path)
        self.passed("lint")
        audit = {}
        for p in sorted((self.repo / "modules/local").rglob("main.nf")):
            audit[str(p.relative_to(self.repo))] = [line for line in p.read_text().splitlines() if any(x in line for x in ("label ", "task.cpus", "container ", "thread", " -p ", " -t "))]
        dump(self.phase / "source-audit.json", audit)
        forbidden = re.compile(r"params\.(?:" + "|".join(FLAGS) + r")\b")
        for f in ("workflows/annotation_transfer_only.nf", "workflows/euk_scaffold_validation.nf", "subworkflows/local/annotation_transfer.nf", "modules/local/merge_annotations/main.nf"):
            assert not forbidden.search((self.repo / f).read_text()), f
        expected_modules = {'agat/fix_gff', 'classify_unplaced', 'diff_liftoff_copies', 'dnaapler', 'filter_megagenes',
            'fix_gff_names', 'liftoff', 'merge_annotations', 'quast', 'ragtag/correct', 'ragtag/patch', 'ragtag/scaffold',
            'rename_ragtag_scaffolds', 'restore_patch_seqnames', 'samtools/faidx', 'seqtk/fq2fa', 'seqtk/seq', 'tgsgapcloser'}
        assert {str(Path(p).parent.relative_to('modules/local')) for p in audit} == expected_modules
        for module in ('rename_ragtag_scaffolds', 'classify_unplaced'):
            assert "label 'process_single'" in (self.repo / ('modules/local/' + module + '/main.nf')).read_text()
        obsolete = re.compile(r'NO_FILE|emit:\s*unplaced\b|out\.unplaced\b|ragtag_unplaced\.fasta|ragtag\.scaffold\.unplaced\.fasta')
        for folder in ('modules', 'subworkflows', 'workflows', 'tests'):
            for source in (self.repo / folder).rglob('*'):
                if source.suffix in ('.nf', '.config'):
                    assert not obsolete.search(source.read_text()), source
        dump(self.phase / 'module-inventory.json', sorted(expected_modules))
        for frozen in ('main.nf', 'utils/params.nf', 'docs/plans/2026-10-04-resource-contract.md', 'tests/integration/resource_vectors.json'):
            # Immutable base bytes supplied in phase evidence by host Git orchestration.
            assert (self.repo / frozen).read_bytes() == (self.phase / 'base-preserved' / frozen).read_bytes(), frozen
        current = (self.repo / 'nextflow.config').read_text()
        base = (self.phase / 'base-preserved/nextflow.config').read_text()
        assert current[current.index('process {'):] == base[base.index('process {'):]

    def config_matrix(self):
        for profile in ("standard", "docker", "conda", "singularity", "singularity_conda", "test", "test,docker", "docker,test"):
            case = "config-" + profile.replace(",", "-")
            path, output = self.run(case, ["config", self.repo, "-profile", profile, "-flat"])
            assert "params.max_cpus" in output and "process.resourceLimits" in output
            self.no_tasks(path)
            self.passed(case)

    def contract(self):
        self.config_matrix()
        rows = self.vectors["resource_cases"]
        if self.args.parser == "unset":
            rows = [r for r in rows if r["id"] in ("R02", "R03")]
        for row in rows:
            for transport in row["transports"]:
                self.resource(row["id"] + "-" + transport, row["input"], transport, row["expected"], row["mode"])
        self.precedence()
        self.mechanisms()
        self.detection()
        if self.args.parser != "unset":
            self.helpers()

    def fraction_rows(self):
        # Local rounding regressions, deliberately separate from the immutable shared fixture.
        rows = [dict(id="M" + str(i + 1), parameter="max_memory", input=value, expected=count)
            for i, (value, count) in enumerate((("1.2 GB",1288490189), ("2.2 GB",2362232013),
                ("0.9 GB",966367642), ("1.7 GB",1825361101), ("15.9 GB",17072495002),
                ("1.3 GB",1395864371), ("3.3 GB",3543348019), ("7.5 GB",8053063680)))]
        rows += [dict(id="T" + str(i + 1), parameter="max_time", input=value, expected=count)
            for i, (value, count) in enumerate((("1.5ms",2), ("1.0005s",1001), ("1.5ms 1.5ms",4),
                ("1.0005s 1.5ms",1003), ("0.5ms 0.5ms",2), ("1h 30min",5400000)))]
        rows += [dict(id=key, parameter=param, input=value, diagnostic=error) for key,param,value,error in (
            ("OVER-M", "max_memory", "8 EB", "E_MEM"),
            ("OVER-T", "max_time", "9223372036854775808ms", "E_TIME"),
            ("ZERO-T", "max_time", "0.1ms", "E_TIME"),
            ("CLOCK", "max_time", "01:30:00", "E_TIME"))]
        if self.args.parser == "unset":
            rows = [r for r in rows if r["id"] in ("M1", "T1", "T4", "OVER-M", "OVER-T", "CLOCK")]
        return rows

    def fractions(self):
        rows = self.fraction_rows()
        for transport in ("cli", "yaml"):
            case = "F-HELPER-" + transport
            helper_rows = [dict(r, key="fraction_" + str(i), observe_native="diagnostic" not in r) for i,r in enumerate(rows)]
            helper_rows += [dict(id="NATIVE-" + param, parameter=param, input=value, expected=count,
                key="native_" + param, native_object=True, observe_native=True)
                for param,value,count in (("max_memory","1.2 GB",1288490189), ("max_time","1.0005s 1.5ms",1003))]
            self.register(case, transport)
            for r in helper_rows:
                self.coverage_row(r, case, transport, "helper-local", r.get("diagnostic", r.get("expected")))
            if not self.planning:
                values = {r["key"]:r["input"] for r in helper_rows}
                def setup(path):
                    dump(path / "manifest.json", helper_rows)
                    dump(path / "inputs.yaml", values)
                args = ["run", self.repo / "tests/parser_resources/parameters.nf", "-cache", "false", "-work-dir", "{CASE}/work",
                    "--batch_manifest={CASE}/manifest.json", "--batch_output={CASE}/observed.json"]
                args += ["-params-file", "{CASE}/inputs.yaml"] if transport == "yaml" else cli_values(values)
                path, output = self.run(case, args, transport, setup=setup, configs=[self.repo / "nextflow.config", self.safety])
                self.no_tasks(path)
                actual = json.loads((path / "observed.json").read_text())
                assert [r["id"] for r in actual] == [r["id"] for r in helper_rows]
                for wanted, got in zip(helper_rows, actual):
                    if "diagnostic" in wanted:
                        self.diagnostic(got["error"], wanted["diagnostic"], wanted["input"], transport, wanted["parameter"])
                    else:
                        assert got.get("value") == got.get("native_value") == wanted["expected"], (wanted, got)
                        if wanted.get("native_object"):
                            assert got["native_identity"] is True, got
                self.passed(case)
            for r in rows:
                case = "F-CONFIG-" + r["id"] + "-" + transport
                expected_exit = "nonzero" if "diagnostic" in r else "zero"
                self.register(case, transport, expected_exit)
                if not self.planning:
                    values = dict(max_cpus=1, max_memory="512 MB", max_time="30min")
                    values[r["parameter"]] = r["input"]
                    if "diagnostic" not in r:
                        cap = [1, r["expected"] if r["parameter"] == "max_memory" else 536870912,
                            r["expected"] if r["parameter"] == "max_time" else 1800000]
                        self.resource(case, values, transport, expected_tiers(cap), "resolution_only")
                    else:
                        def setup_negative(path):
                            dump(path / "inputs.yaml", values)
                        args = ["run", self.repo / "tests/integration/resource_probe.nf", "-cache", "false", "-work-dir", "{CASE}/work",
                            "--probe_mode=resolution_only", "--outdir={CASE}/results"]
                        args += ["-params-file", "{CASE}/inputs.yaml"] if transport == "yaml" else cli_values(values)
                        path, output = self.run(case, args, transport, "nonzero", setup=setup_negative,
                            configs=[self.repo / "nextflow.config", self.safety])
                        self.diagnostic(output, r["diagnostic"], r["input"], transport, r["parameter"])
                        self.no_tasks(path)
                        assert not list((path / "work").rglob("resolved.json"))
                        self.passed(case)
                self.entry("F-ENTRY-" + r["id"] + "-" + transport, transport=transport,
                    expected=expected_exit, error=(r["parameter"],r["diagnostic"]) if "diagnostic" in r else None,
                    invalid=r["input"], **{transport:{r["parameter"]:r["input"]}})
        self.register("F-CONFIG-NATIVE", "config")
        if not self.planning:
            config = self.phase / "native.config"
            config.write_text("params.max_cpus = 1\nparams.max_memory = new nextflow.util.MemoryUnit('1.2 GB')\n"
                              "params.max_time = new nextflow.util.Duration('1.0005s 1.5ms')\n")
            self.resource("F-CONFIG-NATIVE", expected=expected_tiers([1,1288490189,1003]),
                mode="resolution_only", extra_configs=[config])

    def precedence(self):
        rows = self.vectors["precedence_cases"]
        if self.args.parser == "unset":
            rows = [r for r in rows if r["id"] == "P06"]
        fixture = self.phase / "precedence-inputs"
        fixture.mkdir()
        (fixture / "RUN.txt").write_text((self.phase / "RUN.txt").read_text())
        for row in rows:
            directory = fixture / row["id"]
            directory.mkdir()
            layers = row["overrides"]
            configs = []
            for stage in row["stages"]:
                if stage not in ("project", "c1", "c2"):
                    continue
                text = "\n".join("params.%s = %s" % (k, json.dumps(v)) for k, v in layers[stage].items()) + "\n"
                if stage == "c2":
                    # The profile exists even in P03; selection is a separate engine argument.
                    values = layers.get("profile", dict(max_cpus=5, max_memory="10 GB", max_time="10h"))
                    text += "profiles {\n contract_profile {\n" + "\n".join("params.%s = %s" % (k, json.dumps(v)) for k, v in values.items()) + "\n }\n}\n"
                path = directory / (stage + ".config")
                path.write_text(text)
                configs.append(path)
            args = []
            if "profile" in row["stages"]:
                args += ["-profile", "contract_profile"]
            if "yaml" in row["stages"]:
                path = directory / "params.yaml"
                dump(path, layers["yaml"])
                args += ["-params-file", str(path)]
            effective = row["expected_effective"]
            expected = expected_tiers([effective[k] for k in ("cpus", "memory_bytes", "time_ms")])
            self.resource(row["id"], layers.get("cli", {}), "cli", expected, extra_configs=configs, extra_args=args)

    def mechanisms(self):
        inputs = dict(max_cpus=1, max_memory="512 MB", max_time="30min")
        expected = expected_tiers([1, 536870912, 1800000])
        for case, name, mode in (("L01", "PROBE_HIGH", "execute"), ("L02", "ALIAS_PATH:ALIASED", "alias")):
            if self.args.parser == "unset" and case != "L01":
                continue
            config = self.phase / (case + ".config")
            config.write_text("process { withName: '" + name + "' { cpus = 99; memory = '99 GB'; time = '999h' } }\n")
            self.resource(case, inputs, expected=expected if mode == "execute" else {"alias": [1,536870912,1800000]},
                          mode=mode, extra_configs=[config])
        if self.args.parser != "unset":
            self.resource("L03", inputs, expected={"retry": [1,536870912,1800000]}, mode="retry")

    def detection(self):
        for case, processors in (("D01", 4), ("D02", 1)):
            if self.args.parser == "unset" and case != "D01":
                continue
            env = dict(NXF_OPTS="-Xmx768m -XX:ActiveProcessorCount=" + str(processors))
            raw_path, output = self.run(case + "-raw", ["run", self.repo / "tests/parser_resources/detect.nf", "-cache", "false", "-work-dir", "{CASE}/work"], env=env)
            raw = next(json.loads(line) for line in output.splitlines() if line.startswith('{"raw_cpus"'))
            assert raw["raw_cpus"] == processors
            meminfo = Path("/proc/meminfo").read_text()
            (raw_path / "meminfo.txt").write_text(meminfo)
            kb = int(re.search(r"MemTotal:\s+(\d+)\s+kB", meminfo)[1])
            cap = [max(1, processors - 2), max(1, kb // 1048576 - 2) * 1073741824, 604800000]
            self.no_tasks(raw_path)
            self.passed(case + "-raw")
            self.resource(case, expected=expected_tiers(cap), env=env)
        if self.args.parser != "unset":
            env = dict(NXF_OPTS="-Xms64m -Xmx5g -XX:ActiveProcessorCount=4")
            raw_path, output = self.run("D03-raw", ["run", self.repo / "tests/parser_resources/detect.nf", "-cache", "false", "-work-dir", "{CASE}/work"], env=env)
            raw = next(json.loads(line) for line in output.splitlines() if line.startswith('{"raw_cpus"'))
            assert raw["raw_max_memory"] >= 5 * 1073741824
            self.no_tasks(raw_path)
            self.passed("D03-raw")
            source = (self.repo / "nextflow.config").read_text()
            closure = re.search(r"    max_memory = (\{.*?\n    \}\(\))", source, re.S)[1]
            changed = closure.replace("'/proc/meminfo'", repr(str(self.phase / "nonexistent-meminfo")))
            assert changed != closure and closure.count("'/proc/meminfo'") == 1
            (self.phase / "D03-source-closure.txt").write_text(closure)
            (self.phase / "D03-source-closure.sha256").write_text(hashlib.sha256(closure.encode()).hexdigest() + "\n")
            import difflib
            (self.phase / "D03-one-literal.diff").write_text("".join(difflib.unified_diff(closure.splitlines(True), changed.splitlines(True))))
            config = self.phase / "D03.config"
            config.write_text("params.max_memory = " + changed + "\n")
            path, output = self.run("D03", ["config", "-flat"], env=env, configs=[config])
            memory = max(1, raw["raw_max_memory"] // 1073741824 - 2)
            assert re.search(r"params.max_memory\s*=\s*['\"]?%s GB" % memory, output), output
            self.no_tasks(path)
            self.passed("D03")
            row = next(r for r in self.vectors["resource_cases"] if r["id"] == "R03")
            self.resource("D04", row["input"], expected=row["expected"], env=dict(NXF_OPTS="-Xmx768m -XX:ActiveProcessorCount=4"))


    def helper_rows(self, transport):
        batch = next(b for b in self.vectors["parameter_batches"] if b["transport"] == transport)
        refs = set(batch["case_refs"])
        rows = []
        for vector in self.vectors["negative_cases"]:
            if vector["id"] in refs:
                rows.append(dict(id=vector["id"], parameter=vector["parameter"], input=vector["input"],
                                 diagnostic=vector["diagnostic"]))
        for vector in self.vectors["resource_cases"]:
            if vector["id"] not in refs:
                continue
            for param, field in (("max_cpus", "cpus"), ("max_memory", "memory_bytes"), ("max_time", "time_ms")):
                rows.append(dict(id=vector["id"] + "/" + param, parameter=param, input=vector["input"][param],
                                 expected=vector["effective"][field]))
        for vector in self.vectors["boolean_cases"]:
            if vector["id"] not in refs:
                continue
            if vector["id"].startswith("A"):
                for context in vector["contexts"]:
                    organism = context.get("organism_type")
                    rows.append(dict(id=vector["id"] + "/reorient_assembly/" + (organism or "absent"),
                        parameter="reorient_assembly", organism=organism, input=vector.get("input"),
                        omitted=vector.get("omitted", False), default_value=None, expected=context["expected"]))
            else:
                for flag, default in FLAGS.items():
                    if vector["id"] == "BN09" and flag == "reorient_assembly":
                        continue
                    row = dict(id=vector["id"] + "/" + flag, parameter=flag, input=vector.get("input"),
                               omitted=vector.get("omitted", False), default_value=default, organism="fungal")
                    if "diagnostic" in vector:
                        row["diagnostic"] = "E_AUTO" if flag == "reorient_assembly" else "E_BOOL"
                    else:
                        row["expected"] = (False if default is None else default) if vector.get("omitted") else vector["expected"]
                    rows.append(row)
        for index, row in enumerate(rows):
            row["key"] = "case_%04d" % index
        return rows

    def helpers(self):
        batches = {}
        for transport in ("yaml", "cli"):
            case = "H-" + transport.upper()
            rows = self.helper_rows(transport)
            batches[transport] = rows
            self.register(case, transport)
            for row in rows:
                self.coverage_row(row, case, transport, "helper", row.get("diagnostic", row.get("expected")))
        self.write_tables()
        for transport, rows in batches.items():
            case = "H-" + transport.upper()
            values = {r["key"]: r["input"] for r in rows if not r.get("omitted")}
            def setup(path):
                dump(path / "manifest.json", rows)
                dump(path / "inputs.yaml", values)
            args = ["run", self.repo / "tests/parser_resources/parameters.nf", "-cache", "false",
                    "-work-dir", "{CASE}/work", "--batch_manifest={CASE}/manifest.json", "--batch_output={CASE}/observed.json"]
            if transport == "yaml":
                args += ["-params-file", "{CASE}/inputs.yaml"]
            else:
                args += cli_values(values)
            path, output = self.run(case, args, transport, setup=setup, configs=[self.repo / "nextflow.config", self.safety])
            self.no_tasks(path)
            records = json.loads((path / "observed.json").read_text())
            assert len(records) == len(rows)
            assert [r["id"] for r in records] == [r["id"] for r in rows]
            for expected, actual in zip(rows, records):
                if "diagnostic" in expected:
                    assert "error" in actual, (expected, actual)
                    self.diagnostic(actual["error"], expected["diagnostic"], expected.get("input"), transport, expected["parameter"])
                else:
                    assert "error" not in actual, (expected, actual)
                    assert actual["value"] == expected["expected"], (expected, actual)
                    if expected["parameter"] in FLAGS:
                        assert actual["type"] == "java.lang.Boolean", actual
                    else:
                        assert actual["type"] in ("java.lang.Integer", "java.lang.Long"), actual
            self.passed(case)
            print("%s: %s helper assertion rows, zero tasks" % (case, len(rows)), flush=True)

    def entry(self, case, route="full", cli=None, yaml=None, config=None, expected="zero",
              error=None, invalid=None, transport="cli", organism="fungal", legacy=False, membership=None, omit_selector=False):
        if self.planning:
            self.register(case, transport, expected)
            return
        values = dict(assembly=str(self.fixture / "assembly.fasta"), reference=str(self.fixture / "reference.fasta"),
            reference_gff=str(self.fixture / "reference.gff3"), vendor_gff=str(self.fixture / "vendor.gff3"),
            reads=str(self.fixture / "reads.fastq"), **self.caps)
        if not omit_selector:
            values["workflow"] = route
        if organism is not None:
            values["organism_type"] = organism
        # Cases that exercise YAML or config must leave their keys absent from CLI defaults.
        for key in (yaml or {}):
            values.pop(key, None)
        values.update(cli or {})
        def setup(path):
            dump(path / "inputs.yaml", yaml or {})
            dump(path / "resolved-input-layers.json", dict(cli=values, yaml=yaml or {}, config=config or {}))
            (path / "overrides.config").write_text("\n".join("params.%s = %s" % (k, json.dumps(v)) for k,v in (config or {}).items()) + "\n")
        args = ["run", self.repo / "main.nf", "-preview", "-cache", "false", "-work-dir", "{CASE}/work",
                "-profile", "test,docker", "-params-file", "{CASE}/inputs.yaml", "--outdir={CASE}/results"]
        if legacy:
            args += ["-entry", "ANNOTATION_TRANSFER_ONLY"]
        args += cli_values(values)
        path, output = self.run(case, args, transport, expected, setup=setup,
                               configs=[self.phase / case / "overrides.config", self.safety])
        self.no_tasks(path)
        if error:
            parameter, key = error
            self.diagnostic(output, key, invalid, transport, parameter)
        else:
            prefix = "ANNOTATION_TRANSFER_WORKFLOW" if route == "annotation_transfer_only" else "EUK_SCAFFOLD_VALIDATION"
            if legacy:
                prefix = "ANNOTATION_TRANSFER_ONLY:" + prefix
            created = re.findall(r"Creating process '([^']+)'", (path / ".nextflow.log").read_text())
            dump(path / "created-processes.json", created)
            assert prefix + ":QUAST" in created, created
            if legacy:
                info = "INFO: Legacy -entry ANNOTATION_TRANSFER_ONLY selects annotation_transfer_only; --workflow does not select the route."
                assert output.count(info) == 1
            for process, enabled in (membership or {}).items():
                assert (prefix + ":" + process in created) == enabled, (case, process, enabled, created)
        self.passed(case)

    def entry_parameters(self):
        cases = []
        negatives = {row["id"]: row for row in self.vectors["negative_cases"]}
        for route in ROUTES:
            for recipe in self.vectors["entry_cases"]:
                id = recipe["id"]
                expand = recipe["expand"]
                selections = list(FLAGS) if expand == "flags" else list(self.caps) if expand == "dimensions" else [None]
                for selected in selections:
                    nullable = "nullable" if selected == "reorient_assembly" else "nonnullable"
                    layers = {}
                    for transport, assignments in recipe["layers"].items():
                        resolved = {}
                        for key, value in assignments.items():
                            if key == "all_flags":
                                resolved.update(dict.fromkeys(FLAGS, value))
                            elif key == "lexicographically_first_flag":
                                resolved[sorted(FLAGS)[0]] = value
                            elif key == "selected_flag":
                                resolved[selected] = value
                            elif key == "selected_flag_by_nullability":
                                resolved[selected] = value[nullable]
                            elif key == "selected_dimension_case":
                                resolved[selected] = negatives[value[selected]]["input"]
                            else:
                                resolved[key] = value
                        layers[transport] = resolved
                    case = id + "-" + route + ("-" + selected if selected else "")
                    spec = dict(case=case, route=route, **layers, expected=recipe["expected_exit"])
                    transport = "cli" if id.endswith("CLI") else "yaml" if id.endswith("YAML") else "layers"
                    spec["transport"] = transport
                    if recipe["expected_exit"] == "nonzero":
                        key = recipe["diagnostic"][nullable if expand == "flags" else selected]
                        spec.update(error=(selected, key), invalid=layers[transport][selected])
                    if expand == "nullable_routes":
                        context = recipe["route_contexts"][route]
                        organism = context.get("organism_type")
                        spec.update(organism=organism, membership={"DNAAPLER": organism == "bacterial"})
                    cases.append(spec)
                    flags = [selected] if selected else ["reorient_assembly"] if expand == "nullable_routes" else list(FLAGS)
                    for flag in flags:
                        self.coverage_row(dict(id=id + "/" + route, parameter=flag,
                            organism=spec.get("organism") or ("absent" if expand == "nullable_routes" else "")),
                            case, transport, "entry", recipe["expected_exit"])
        assert len(cases) == 64
        for spec in cases:
            self.register(spec["case"], spec["transport"], spec["expected"])
        self.write_tables()
        for spec in cases:
            self.entry(**spec)

    def previews(self):
        for case, route, omit in (("SEL-DEFAULT", "full", True), ("SEL-FULL", "full", False),
                                  ("SEL-ANNOTATION", "annotation_transfer_only", False)):
            self.entry(case, route=route, omit_selector=omit)
        for transport in ("cli", "yaml"):
            for label, value in (("INVALID","bogus"), ("EMPTY","")):
                self.entry("SEL-" + label + "-" + transport, **{transport:{"workflow":value}},
                    expected="nonzero", error=("workflow", "E_WORKFLOW"), invalid=value, transport=transport)
        self.entry("SEL-NULL", yaml={"workflow":None}, expected="nonzero", error=("workflow","E_WORKFLOW"), invalid=None, transport="yaml")
        # YAML preserves whitespace that CLI transport may trim.
        self.entry("SEL-WHITESPACE", yaml={"workflow":"full "}, expected="nonzero", error=("workflow","E_WORKFLOW"), invalid="full ", transport="yaml")
        for route in ROUTES:
            for organism in (("fungal", "bacterial") if route == "full" else (None, "fungal", "bacterial")):
                for flag, value in (("auto", None), ("false", False), ("true", True)):
                    self.entry("AUTO-%s-%s-%s" % (route, organism or "absent", flag), route=route,
                        yaml={"reorient_assembly":value}, organism=organism, membership={"DNAAPLER": value if value is not None else organism == "bacterial"})
            for transport in ("cli", "yaml"):
                for value in (0, 10000):
                    self.entry("NUMERIC-%s-%s-%s" % (route, transport, value), route=route, **{transport:{"max_gene_length_bp":value}})
        if self.args.parser == "unset":
            self.entry("UNSET-CAP", cli={"max_cpus":-1}, expected="nonzero", error=("max_cpus","E_CPU"), invalid=-1)
            self.entry("UNSET-BOOL", cli={"merge_novel_only":"yes"}, expected="nonzero", error=("merge_novel_only","E_BOOL"), invalid="yes")

    def legacy_entry(self):
        assert self.args.parser == "v1"
        for name, value in (("DEFAULT", None), ("FULL","full"), ("ANNOTATION","annotation_transfer_only")):
            self.entry("LEG-" + name, route="annotation_transfer_only", legacy=True, organism=None,
                       omit_selector=value is None, cli={} if value is None else {"workflow":value})
        for name, param, value, error in (("INVALID","workflow","bogus","E_WORKFLOW"),
                                        ("CAP","max_cpus",-1,"E_CPU"), ("BOOL","merge_novel_only","yes","E_BOOL")):
            self.entry("LEG-" + name, route="annotation_transfer_only", legacy=True, organism=None,
                       cli={param:value}, expected="nonzero", error=(param,error), invalid=value)

    def unsupported(self):
        assert self.args.engine == "26.04.5"
        values = dict(assembly=str(self.fixture / "assembly.fasta"), reference=str(self.fixture / "reference.fasta"),
            reference_gff=str(self.fixture / "reference.gff3"), reads=str(self.fixture / "reads.fastq"),
            organism_type="fungal", **self.caps)
        path, output = self.run("floor", ["run", self.repo / "main.nf", "-preview", "-cache", "false",
            "-work-dir", "{CASE}/work", "--outdir={CASE}/results"] + cli_values(values), expected="nonzero", configs=[self.safety])
        assert "26.04.5" in output and ">=26.04.6" in output and re.search(r"version|requires", output, re.I), output
        assert not re.search(r"Script compilation error|Unknown variable|not found", output), output
        self.no_tasks(path)
        self.passed("floor")


    def docker_overlay(self, path):
        self.trace_config(path)
        binary = str(self.repo / "bin")
        run_options = "-u %s:%s -v %s:%s:ro -v %s:%s:ro" % (
            os.getuid(), os.getgid(), binary, binary, self.repo, self.repo)
        (path / "docker.config").write_text(
            "process.maxForks = 1\nexecutor.queueSize = 1\nconda.enabled = false\nsingularity.enabled = false\n"
            "docker.enabled = true\ndocker.runOptions = " + repr(run_options) + "\n"
            "process.beforeScript = " + repr('export PATH="' + binary + ':$PATH"') + "\n"
            "env.PATH = " + repr(binary + ':$PATH') + "\n"
            "report.enabled = false\ntimeline.enabled = false\ndag.enabled = false\n")
        result = subprocess.run(["docker", "version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (path / "docker-version.txt").write_text(result.stdout)
        assert result.returncode == 0

    def actual_trace(self, path, caps, expected=None):
        with (path / "trace.tsv").open() as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            assert reader.fieldnames == ["task_id", "hash", "name", "status", "exit", "cpus", "memory", "time"]
            rows = list(reader)
        assert rows
        directives = []
        for row in rows:
            assert row["status"] == "COMPLETED" and row["exit"] == "0", row
            request = [int(row[k]) for k in ("cpus", "memory", "time")]
            assert all(0 < value <= cap for value, cap in zip(request, caps)), row
            if expected is not None:
                assert request == expected, row
            work = list((path / "work").glob(row["hash"] + "*"))
            assert len(work) == 1, (row, work)
            wrapper = (work[0] / ".command.run").read_text()
            assert re.search(r"--cpu-shares[ =]+%s\b" % (int(row["cpus"]) * 1024), wrapper), wrapper
            assert "--memory" in wrapper
            memory_arg = re.search(r"--memory[ =]+([0-9]+)([a-zA-Z]*)", wrapper)
            assert memory_arg
            multiplier = {"":1, "b":1, "k":1024, "m":1048576, "g":1073741824}[memory_arg[2].lower()]
            assert int(memory_arg[1]) * multiplier == int(row["memory"]), wrapper
            tier = "single" if any(n in row["name"] for n in ('RENAME_RAGTAG', 'CLASSIFY_UNPLACED')) else "medium" if any(n in row["name"] for n in ('LIFTOFF', 'RAGTAG_')) else "low"
            assert request == expected_tiers(caps)[tier], row
            directives.append(dict(row, tier=tier, attempt=1, transport="docker"))
            self.results.append(dict(contract="cc-resource-v1", case=path.name, engine=self.args.engine,
                parser=self.args.parser, transport="docker", tier=tier, attempt=1, cpus=request[0],
                memory_bytes=request[1], time_ms=request[2], expectation=json.dumps(expected_tiers(caps)[tier]), status="PASS"))
        dump(path / "actual-directives.json", directives)
        self.write_tables()
        return rows

    def docker_rename(self):
        case = "RENAME"
        def setup(path):
            self.docker_overlay(path)
        path, output = self.run(case, ["run", self.repo / "tests/parser_resources/rename.nf",
            "-cache", "false", "-work-dir", "{CASE}/work", "-profile", "docker",
            "--outdir={CASE}/results", "--fixture=" + str(self.fixture), "--test_kind=rename",
            "--sample_name=fixture", "--max_cpus=1", "--max_memory=512 MB", "--max_time=30min"],
            setup=setup, configs=[self.repo / "nextflow.config", self.phase / case / "docker.config", self.phase / case / "trace-resources.config"])
        rows = self.actual_trace(path, [1,536870912,1800000], [1,536870912,1800000])
        assert len(rows) == 1
        work = next((path / "work").rglob(".command.sh")).parent
        assert (work / "fixture_scaffolds.fasta").read_text() == ">fixture_chr1\nACGTACGTACGT\n>fixture_unplaced1\nGGGAAACCC\n"
        assert not list((path / 'results').rglob('*unplaced.fasta'))
        wrapper = (work / ".command.run").read_text()
        binary = str(self.repo / "bin")
        assert binary + ":" + binary in wrapper and 'export PATH="' + binary + ':$PATH"' in wrapper
        self.passed(case)

    def annotation_smoke(self):
        case = "ANNOTATION"
        def setup(path):
            self.docker_overlay(path)
        values = dict(workflow="annotation_transfer_only", organism_type="fungal",
            assembly=str(self.fixture / "assembly.fasta"), reference=str(self.fixture / "reference.fasta"),
            reference_gff=str(self.fixture / "reference.gff3"), vendor_gff=str(self.fixture / "vendor.gff3"),
            reorient_assembly=False, fix_reference_gff=False, fix_vendor_gff=False, liftoff_copies=False,
            merge_novel_only=True, max_cpus=1, max_memory="4 GB", max_time="1h", sample_name="fixture")
        path, output = self.run(case, ["run", self.repo / "main.nf", "-cache", "false", "-work-dir", "{CASE}/work",
            "-profile", "test,docker", "--outdir={CASE}/results"] + cli_values(values),
            setup=setup, configs=[self.phase / case / "docker.config", self.phase / case / "trace-resources.config"])
        rows = self.actual_trace(path, [1,4294967296,3600000])
        names = [r["name"] for r in rows]
        assert any(":QUAST" in n for n in names)
        assert any(":MERGE_ITERATIVE" in n for n in names)
        assert not any(any(x in n for x in ("MERGE_FULL", "COPIES", "DNAAPLER", "AGAT")) for n in names), names
        assert not any(any(x in n for x in ('SCAFFOLD', 'CLASSIFY_UNPLACED', 'RENAME_RAGTAG')) for n in names)
        assert not list((path / 'results').rglob('*unplaced_contigs.tsv'))
        gff = path / "results/final_outputs/fixture_merged_iterative.gff3"
        assert gff.is_file() and "\tgene\t" in gff.read_text()
        assert all(line.startswith("chr1\t") for line in gff.read_text().splitlines() if line and not line.startswith("#"))
        assert not list((path / "results").rglob("fixture_merged.gff3"))
        commands = "\n".join(p.read_text() for p in (path / "work").rglob(".command.sh"))
        assert "--novel-only" in commands and not re.search(r"\s-copies\b", commands)
        assert re.search(r"\s-p 1\b", commands) and re.search(r"--threads 1\b", commands)
        self.passed(case)
        # Real commands for the migration-only false/null/zero handling, without rerunning Liftoff.
        for transport, value, tag in (("yaml", None, "null"), ("cli", 0, "zero"), ("yaml", 0, "zero"),
                                       ("cli", 10000, "positive"), ("yaml", 10000, "positive")):
            case = "COMMANDS-" + transport + "-" + tag
            def setup_commands(path):
                self.docker_overlay(path)
                dump(path / "inputs.yaml", {"max_gene_length_bp":value, "merge_novel_only":False} if transport == "yaml" else {})
            args = ["run", self.repo / "tests/parser_resources/rename.nf", "-cache", "false", "-work-dir", "{CASE}/work",
                    "-profile", "docker", "--outdir={CASE}/results", "--fixture=" + str(self.fixture),
                    "--test_kind=commands", "--sample_name=fixture", "--max_cpus=1", "--max_memory=4 GB", "--max_time=1h",
                    "-params-file", "{CASE}/inputs.yaml"]
            if transport == "cli":
                args += cli_values(dict(max_gene_length_bp=value, merge_novel_only=False))
            path, output = self.run(case, args, transport, setup=setup_commands,
                configs=[self.repo / "nextflow.config", self.phase / case / "docker.config", self.phase / case / "trace-resources.config"])
            rows = self.actual_trace(path, [1,4294967296,3600000], [1,1073741824,3600000])
            assert len(rows) == 2
            commands = "\n".join(p.read_text() for p in (path / "work").rglob(".command.sh"))
            assert "--novel-only" not in commands
            assert ("--max-length-bp 10000" in commands) == (value == 10000)
            if value != 10000:
                assert "--max-length-bp" not in commands
            self.passed(case)


    def integration_resources(self):
        for profile in ('docker', 'test,docker'):
            case = 'config-' + profile.replace(',', '-')
            self.register(case)
            if not self.planning:
                path, output = self.run(case, ['config', self.repo, '-profile', profile, '-flat'])
                assert 'params.max_cpus' in output and 'process.resourceLimits' in output
                self.no_tasks(path)
                self.passed(case)
        for case, ref, transport in (('R02-cli', 'R02', 'cli'), ('R03-yaml', 'R03', 'yaml')):
            self.register(case, transport)
            if not self.planning:
                row = self.resources[ref]
                self.resource(case, row['input'], transport, row['expected'], row['mode'])
        self.register('L02')
        if not self.planning:
            config = self.phase / 'L02.config'
            config.write_text("process { withName: 'ALIAS_PATH:ALIASED' { cpus = 99; memory = '99 GB'; time = '999h' } }\n")
            self.resource('L02', self.resources['R02']['input'], expected={'alias':[1,536870912,1800000]},
                          mode='alias', extra_configs=[config])

    def no_first_warning(self, path):
        for name in ('output.log', '.nextflow.log'):
            assert 'The operator `first` is useless when applied to a value channel' not in (path / name).read_text(), path

    def scaffolding_preview(self):
        cases = [
            dict(case='PREVIEW-DEFAULT', omit_selector=True, cli={'run_correct':False, 'reorient_assembly':False},
                 membership={'SCAFFOLDING:RAGTAG_CORRECT':False, 'DNAAPLER':False}),
            dict(case='PREVIEW-CORRECT', cli={'run_correct':True, 'reorient_assembly':False},
                 yaml={'scaffold_rename_pattern':r'_(Chr[IVXLCDM]+)$'},
                 membership={'SCAFFOLDING:RAGTAG_CORRECT':True, 'DNAAPLER':False}),
            dict(case='PREVIEW-BACTERIAL', organism='bacterial', cli={'run_correct':False, 'scaffold_rename_pattern':r'_(Chr[IVXLCDM]+)$'},
                 membership={'SCAFFOLDING:RAGTAG_CORRECT':False, 'DNAAPLER':True}),
            dict(case='PREVIEW-ANNOTATION', route='annotation_transfer_only', organism=None,
                 membership={'SCAFFOLDING:RAGTAG_SCAFFOLD':False, 'SCAFFOLDING:CLASSIFY_UNPLACED':False,
                             'SCAFFOLDING:RENAME_RAGTAG_SCAFFOLDS':False, 'DNAAPLER':False}),
            dict(case='PREVIEW-INVALID', cli={'workflow':'bogus'}, expected='nonzero', error=('workflow','E_WORKFLOW'), invalid='bogus')]
        for spec in cases:
            if spec.get('route', 'full') == 'full' and not spec.get('error'):
                spec['membership'].update({'SCAFFOLDING:RAGTAG_SCAFFOLD':True, 'SCAFFOLDING:CLASSIFY_UNPLACED':True,
                                           'SCAFFOLDING:RENAME_RAGTAG_SCAFFOLDS':True})
            self.entry(**spec)
            if not self.planning and spec.get('route','full') == 'full' and not spec.get('error'):
                self.no_first_warning(self.phase / spec['case'])
        if not self.planning:
            wiring = (self.repo / 'subworkflows/local/scaffolding.nf').read_text()
            assert 'CLASSIFY_UNPLACED(RAGTAG_SCAFFOLD.out.agp, RAGTAG_SCAFFOLD.out.confidence)' in wiring
            assert 'reference_fai' not in wiring
            calls = (self.repo / 'workflows/euk_scaffold_validation.nf').read_text()
            assert 'SCAFFOLDING(ch_assembly, ch_reference, ch_reads_scaffold, true)' in calls
            assert "SCAFFOLDING(ch_assembly, ch_reference, Channel.value(file('NO_READS')), false)" in calls

    def task_work(self, path, rows, process):
        selected = [r for r in rows if r['name'].split(':')[-1].split(' (')[0] == process]
        assert len(selected) == 1, (process, rows)
        work = list((path / 'work').glob(selected[0]['hash'] + '*'))
        assert len(work) == 1
        return selected[0], work[0]

    def publication(self, path, expected):
        for destination in ('scaffold', 'final_outputs'):
            actual = path / ('results/' + destination + '/fixture_unplaced_contigs.tsv')
            assert actual.read_text() == expected, actual
        assert not list((path / 'results').rglob('*unplaced.fasta'))

    def provenance(self, path, rows, queries):
        scaffold, sw = self.task_work(path, rows, 'RAGTAG_SCAFFOLD')
        classifier, cw = self.task_work(path, rows, 'CLASSIFY_UNPLACED')
        commands = (cw / '.command.sh').read_text()
        assert '--agp ragtag.scaffold.agp' in commands and '--confidence ragtag.scaffold.confidence.txt' in commands
        assert '--fai' not in commands
        observed = []
        for name in ('ragtag.scaffold.agp', 'ragtag.scaffold.confidence.txt'):
            emitted, staged = sw / 'ragtag_out' / name, cw / name
            assert staged.is_symlink(), staged
            assert staged.resolve() == emitted.resolve(), (staged, emitted)
            digest = hashlib.sha256(emitted.read_bytes()).hexdigest()
            assert hashlib.sha256(staged.read_bytes()).hexdigest() == digest
            published = path / 'results/scaffold' / name
            assert published.read_bytes() == emitted.read_bytes()
            observed.append(dict(filename=name, emitted=str(emitted), staged=str(staged),
                                 readlink_f=str(staged.resolve()), sha256=digest))
        confidence = (sw / 'ragtag_out/ragtag.scaffold.confidence.txt').read_text().splitlines()
        assert confidence[0] == 'query\tgrouping_confidence\tlocation_confidence\torientation_confidence'
        assert {line.split('\t')[0] for line in confidence[1:] if line} == set(queries), confidence
        assert re.search(r'-t 1\b', (sw / '.command.sh').read_text())
        dump(path / 'same-task-provenance.json', dict(scaffold=scaffold, classifier=classifier, files=observed))

    def rename_preservation(self, path, original, expected_ids):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('scaffolding_helpers', self.repo / 'tests/scaffolding/helpers.py')
        helper = module_from_spec(spec)
        spec.loader.exec_module(helper)
        before = helper.records(original)
        after = helper.records(path / 'results/scaffold/fixture_scaffolds.fasta')
        assert [r[0] for r in after] == expected_ids, after
        assert [r[1] for r in before] == [r[1] for r in after], (before, after)
        dump(path / 'rename-preservation.json', dict(original_ids=[r[0] for r in before], renamed_ids=expected_ids,
            lengths=[len(r[1]) for r in after], sequence_sha256=[hashlib.sha256(r[1].encode()).hexdigest() for r in after]))
        return after

    def generate_inputs(self, path, kind):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('scaffolding_helpers', self.repo / 'tests/scaffolding/helpers.py')
        helper = module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.generate(self.repo, path / 'inputs', kind)

    def scaffolding_modules(self):
        cases = [('MODULE-MIXED', 'R02'), ('MODULE-QUOTED', 'R03'), ('MODULE-PLACED', 'R02'), ('CORRECTION', None)]
        if self.args.parser == 'v1':
            cases = cases[:1]
        negatives = [('PATTERN-FALSE',False), ('PATTERN-ZERO',0), ('PATTERN-EMPTY',''), ('PATTERN-MAP',{})] if self.args.parser == 'v2' else []
        for case, ref in cases:
            self.register(case, 'yaml' if case == 'MODULE-QUOTED' else 'cli')
        for case, value in negatives:
            self.register(case, 'yaml', 'nonzero')
        if self.planning:
            return
        for case, ref in cases:
            cap = [1,4294967296,3600000] if ref is None else [self.resources[ref]['effective'][k] for k in ('cpus','memory_bytes','time_ms')]
            def setup(path):
                self.docker_overlay(path)
                self.generate_inputs(path, case)
                dump(path / 'params.yaml', dict(self.resources['R03']['input'], scaffold_rename_pattern=r"-(Chr[IVX]+)'$") if case == 'MODULE-QUOTED' else {})
            values = dict(sample_name='fixture', assembly='{CASE}/inputs/assembly.fasta',
                test_kind='correct' if ref is None else 'mixed', outdir='{CASE}/results')
            if ref is None:
                values.update(reference='{CASE}/inputs/reference.fasta', reads='{CASE}/inputs/reads.fastq',
                              max_cpus=1, max_memory='4 GB', max_time='1h')
            else:
                values.update(agp='{CASE}/inputs/scaffold.agp', confidence='{CASE}/inputs/confidence.txt')
                if case != 'MODULE-QUOTED':
                    values.update(self.resources[ref]['input'])
            path, output = self.run(case, ['run', self.repo / 'tests/scaffolding/modules.nf', '-profile','docker', '-cache','false',
                '-work-dir','{CASE}/work','-params-file','{CASE}/params.yaml'] + cli_values(values),
                'yaml' if case == 'MODULE-QUOTED' else 'cli', setup=setup,
                configs=[self.repo / 'nextflow.config', self.phase / case / 'docker.config', self.phase / case / 'trace-resources.config'])
            rows = self.actual_trace(path, cap)
            assert len(rows) == (4 if ref is None else 2), rows
            self.publication(path, (path / 'inputs/expected.tsv').read_text())
            if ref is None:
                self.provenance(path, rows, ['contig_3_1_30000_+'])
                _, corrected = self.task_work(path, rows, 'RAGTAG_CORRECT')
                assert re.search(r'-t 1\b', (corrected / '.command.sh').read_text())
                assert '-u' in (corrected / '.command.sh').read_text()
                _, sw = self.task_work(path, rows, 'RAGTAG_SCAFFOLD')
                self.rename_preservation(path, sw / 'ragtag_out/ragtag.scaffold.fasta', ['fixture_chr1'])
            else:
                assert {r['name'].split(':')[-1].split(' (')[0] for r in rows} == {'RENAME_RAGTAG_SCAFFOLDS','CLASSIFY_UNPLACED'}
                self.rename_preservation(path, path / 'inputs/assembly.fasta',
                    ["fixture_ChrI" if case == 'MODULE-QUOTED' else 'fixture_strain_ChrI', 'fixture_2micron_plasmid'])
            self.passed(case)
        for case, value in negatives:
            def setup(path):
                self.docker_overlay(path)
                self.generate_inputs(path, 'MODULE-MIXED')
                dump(path / 'params.yaml', {'scaffold_rename_pattern':value})
            args = ['run', self.repo / 'tests/scaffolding/modules.nf', '-profile','docker', '-cache','false', '-work-dir','{CASE}/work',
                    '-params-file','{CASE}/params.yaml'] + cli_values(dict(self.resources['R02']['input'], sample_name='fixture',
                    assembly='{CASE}/inputs/assembly.fasta', outdir='{CASE}/results', test_kind='rename'))
            path, output = self.run(case, args, 'yaml', 'nonzero', setup=setup,
                configs=[self.repo / 'nextflow.config', self.phase / case / 'docker.config', self.phase / case / 'trace-resources.config'])
            assert 'ERROR: --scaffold_rename_pattern must be null or a nonempty string.' in output, output
            assert not list((path / 'results').rglob('*scaffolds.fasta'))
            assert not list((path / 'work').rglob('fixture_scaffolds.fasta'))
            self.no_tasks(path)
            self.passed(case)

    def scaffolding_smoke(self):
        for case in ('FULL-DEFAULT', 'FULL-PATTERN'):
            self.register(case)
        if self.planning:
            return
        for case in ('FULL-DEFAULT', 'FULL-PATTERN'):
            pattern = case == 'FULL-PATTERN'
            def setup(path):
                self.docker_overlay(path)
                self.generate_inputs(path, case)
            values = dict(workflow='full', assembly='{CASE}/inputs/assembly.fasta', reference='{CASE}/inputs/reference.fasta',
                reference_gff='{CASE}/inputs/reference.gff3', vendor_gff='{CASE}/inputs/vendor.gff3', sample_name='fixture',
                organism_type='bacterial' if pattern else 'fungal', run_correct=False, fill_gaps_from_ref=False, liftoff_copies=False,
                fix_reference_gff=False, fix_vendor_gff=False, fix_generic_names=False, merge_novel_only=True,
                max_cpus=1, max_memory='4 GB', max_time='1h', outdir='{CASE}/results')
            if pattern:
                values['scaffold_rename_pattern'] = r'_(Chr[IVXLCDM]+)$'
            else:
                values['reorient_assembly'] = False
            path, output = self.run(case, ['run', self.repo / 'main.nf', '-profile','docker', '-cache','false', '-work-dir','{CASE}/work'] + cli_values(values),
                setup=setup, configs=[self.phase / case / 'docker.config', self.phase / case / 'trace-resources.config'])
            self.no_first_warning(path)
            rows = self.actual_trace(path, [1,4294967296,3600000])
            names = {r['name'].split(':')[-1].split(' (')[0] for r in rows}
            assert names == {'SAMTOOLS_FAIDX', 'RAGTAG_SCAFFOLD', 'RENAME_RAGTAG_SCAFFOLDS', 'CLASSIFY_UNPLACED', 'SEQTK_SEQ',
                'FILTER_MEGAGENES_REFERENCE', 'FILTER_MEGAGENES_VENDOR', 'LIFTOFF_REFERENCE', 'LIFTOFF_VENDOR', 'MERGE_ITERATIVE', 'QUAST'} | ({'DNAAPLER'} if pattern else set()), names
            self.provenance(path, rows, ['contig_3' if pattern else 'strain_ChrI'])
            self.publication(path, (path / 'inputs/expected.tsv').read_text())
            _, sw = self.task_work(path, rows, 'RAGTAG_SCAFFOLD')
            expected_ids = ['fixture_ChrI' if pattern else 'fixture_strain_ChrI', 'fixture_2micron_plasmid']
            renamed = self.rename_preservation(path, sw / 'ragtag_out/ragtag.scaffold.fasta', expected_ids)
            from importlib.util import spec_from_file_location, module_from_spec
            spec = spec_from_file_location('scaffolding_helpers', self.repo / 'tests/scaffolding/helpers.py')
            helper = module_from_spec(spec)
            spec.loader.exec_module(helper)
            final = helper.records(path / 'results/final_outputs/fixture_final.fasta')
            assert [r[0] for r in final] == expected_ids, final
            if pattern:
                _, dw = self.task_work(path, rows, 'DNAAPLER')
                staged = helper.records(dw / 'fixture_scaffolds.fasta')
                actual = helper.records(dw / 'fixture_reoriented.fasta')
                assert staged == renamed and actual == final
                dump(path / 'dnaapler-records.json', dict(input_ids=[r[0] for r in staged], output_ids=[r[0] for r in actual],
                    input_path=str(dw / 'fixture_scaffolds.fasta'), output_path=str(dw / 'fixture_reoriented.fasta')))
            for (name, original), (final_name, observed) in zip(renamed, final):
                assert name == final_name and len(original) == len(observed)
                reverse = original.translate(str.maketrans('ACGTNacgtn','TGCANtgcan'))[::-1]
                assert (observed in original * 2 or observed in reverse * 2) if pattern else observed == original
            assert dict(final)['fixture_2micron_plasmid'] == helper.generated(20261006) if not pattern else True
            features = [line.split('\t') for line in (path / 'results/final_outputs/fixture_merged_iterative.gff3').read_text().splitlines() if line and not line.startswith('#')]
            assert features and all(len(r) == 9 and r[0] in expected_ids for r in features)
            assert {r[0] for r in features if r[2] == 'gene'} == set(expected_ids), features
            commands = '\n'.join(p.read_text() for p in (path / 'work').rglob('.command.sh'))
            assert not re.search(r'\s-copies\b|--fai\b', commands)
            assert re.search(r'\s-p 1\b', commands) and re.search(r'--threads 1\b', commands)
            self.passed(case)

    def tools(self):
        outcomes = []
        with (self.phase / "tool-inventory.tsv").open() as handle:
            inventory = list(csv.DictReader(handle, delimiter="\t"))
        assert [r["case"] for r in inventory] == ["T-RAGTAG-CORRECT", "T-RAGTAG-SCAFFOLD", "T-RAGTAG-PATCH", "T-LIFTOFF", "T-QUAST", "T-DNAAPLER", "T-TGS"]
        def fasta_sequence(path):
            lines = path.read_text().splitlines()
            assert lines and lines[0].startswith(">"), path
            ids = [line[1:].split()[0] for line in lines if line.startswith(">")]
            assert len(ids) == len(set(ids)) == 1, path
            sequence = "".join(line.strip() for line in lines if not line.startswith(">"))
            assert sequence and re.fullmatch("[ACGTNacgtn]+", sequence), path
            return sequence
        original = fasta_sequence(self.fixture / "assembly.fasta")
        for case in ("T-RAGTAG-CORRECT", "T-RAGTAG-SCAFFOLD", "T-RAGTAG-PATCH", "T-LIFTOFF", "T-QUAST", "T-DNAAPLER", "T-TGS"):
            path = self.phase / case
            source = (path / "source.log").read_text()
            assert (path / "source-exit.txt").read_text().strip() == "0", case
            assert "SOURCE " in source, "Missing pinned source evidence: " + case
            assert re.search(r"thread|process|worker", source, re.I), case
            command = (path / "command.txt").read_text()
            assert re.search(r"(?:-t|\\?-p|--threads?|--thread)[\\ ]+1", command), command
            code = int((path / "exit-code.txt").read_text())
            status, reason = "RUNTIME_PASS", ""
            if code != 0:
                assert case in ("T-DNAAPLER", "T-TGS"), "Required tool runtime failed: " + case
                status = "SOURCE_ONLY_RUNTIME_NOT_VERIFIED"
                reason = "Bounded miniature runtime exited %s; inspect preserved output and pinned source before accepting the limited substitute." % code
            else:
                if case.startswith("T-RAGTAG"):
                    operation = case.split("-")[-1].lower()
                    fasta = path / ("result/ragtag.%s.fasta" % operation)
                    assert fasta.is_file() and fasta.stat().st_size > 0, case
                    assert fasta_sequence(fasta) == original, case
                    agp = path / ("result/ragtag.%s.agp" % operation)
                    parts = [l.split("\t") for l in agp.read_text().splitlines() if l and not l.startswith("#")]
                    assert parts and all(len(p) == 9 for p in parts), case
                    end = 0
                    for index, p in enumerate(parts, 1):
                        assert int(p[1]) == end + 1 and int(p[3]) == index and p[4] == "W", p
                        assert int(p[2]) - int(p[1]) == int(p[7]) - int(p[6]) and p[8] in ("+", "-"), p
                        end = int(p[2])
                    assert end == len(original), case
                elif case == "T-LIFTOFF":
                    text = (path / "lifted.gff3").read_text()
                    assert "\tgene\t" in text and any(l.startswith("chr1\t") for l in text.splitlines())
                    features = [l.split("\t") for l in text.splitlines() if l and not l.startswith("#")]
                    assert {r[2] for r in features} == {"gene", "mRNA", "exon", "CDS"}
                    assert all(len(r) == 9 and r[0] == "chr1" and r[3:5] == ["1001", "1897"] for r in features)
                    assert not (path / "unmapped.txt").read_text().strip()
                elif case == "T-QUAST":
                    assert "fixture" in (path / "result/report.tsv").read_text()
                elif case == "T-DNAAPLER":
                    out = path / "result/fixture_reoriented.fasta"
                    if not out.exists():
                        status, reason = "SOURCE_ONLY_RUNTIME_NOT_VERIFIED", "No marker in deterministic fixture; expected reoriented FASTA absent."
                    else:
                        observed = fasta_sequence(out)
                        reverse = original.translate(str.maketrans("ACGT", "TGCA"))[::-1]
                        assert len(observed) == len(original) and (observed in original * 2 or observed in reverse * 2)
                else:
                    assert fasta_sequence(path / "gapclosed.scaff_seqs") == original
                    assert (path / "gapclosed.gap_fill_detail").read_text().strip() == ">chr1\n1\t30000\tS\t1\t30000"
            outcomes.append(dict(case=case, status=status, reason=reason, source=str(path / "source.log"),
                                 command=str(path / "command.txt"), image=str(path / "image.json")))
            next(r for r in inventory if r["case"] == case)["outcome"] = status
            with (self.phase / "tool-inventory.tsv").open("w") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case", "expected", "outcome"], delimiter="\t")
                writer.writeheader()
                writer.writerows(inventory)
        dump(self.phase / "tool-outcomes.json", outcomes)
        print(json.dumps(outcomes, indent=2))
        # Source-only outcomes are disclosed, never counted as runtime passes.
        assert len(outcomes) == 7

def main():
    parser = argparse.ArgumentParser()
    for arg in ("repo", "phase", "mode", "engine", "parser"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    driver = Driver(args)
    path, output = driver.run("engine-version", ["-version"])
    assert "version " + args.engine in output, output
    driver.no_tasks(path)
    driver.passed("engine-version")
    getattr(driver, args.mode.replace("-", "_"))()
    assert all(row["outcome"] == "PASS" for row in driver.inventory)
    assert all(row["outcome"] == "PASS" for row in driver.coverage)
    print("PASS: %d Nextflow invocations; %d directive records; %d coverage rows. No collected test functions." %
          (len(driver.inventory), len(driver.results), len(driver.coverage)))

if __name__ == "__main__":
    main()
