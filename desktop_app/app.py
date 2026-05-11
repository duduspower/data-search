from __future__ import annotations

import os
import threading
import tkinter as tk
from multiprocessing import freeze_support
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from benchmark import run_benchmark, save_benchmark
from data_access import default_output_path, ensure_dataset, list_datasets, load_dataset, save_records
from query_logic import SearchEngine, field


FIELDS = {
    "id": "int",
    "first_name": "str",
    "last_name": "str",
    "age": "int",
    "city": "str",
    "department": "str",
    "salary": "int",
    "years_experience": "int",
    "is_manager": "bool",
    "skill_level": "str",
    "join_year": "int",
}
OPERATORS_BY_TYPE = {
    "int": ["==", "!=", ">", ">=", "<", "<="],
    "str": ["==", "!=", "contains"],
    "bool": ["==", "!="],
}


def parse_value(field_name: str, raw_value: str) -> Any:
    field_type = FIELDS[field_name]
    value = raw_value.strip()
    if field_type == "int":
        return int(value)
    if field_type == "bool":
        if value.lower() in {"true", "1", "yes", "tak"}:
            return True
        if value.lower() in {"false", "0", "no", "nie"}:
            return False
        raise ValueError("Wartosc bool musi byc true/false, tak/nie albo 1/0.")
    return value


def build_condition(field_name: str, operator: str, value: Any):
    selected = field(field_name)
    if operator == "==":
        return selected == value
    if operator == "!=":
        return selected != value
    if operator == ">":
        return selected > value
    if operator == ">=":
        return selected >= value
    if operator == "<":
        return selected < value
    if operator == "<=":
        return selected <= value
    if operator == "contains":
        return selected.contains(value)
    raise ValueError(f"Nieobslugiwany operator: {operator}")


def combine_conditions(conditions: list[Any], mode: str):
    result = conditions[0]
    for condition in conditions[1:]:
        result = result & condition if mode == "and" else result | condition
    return result


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Wyszukiwanie wartosci w zbiorze danych")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.engine = SearchEngine()
        self.data: list[dict[str, Any]] = []
        self.dataset_path: Path | None = None
        self.last_results: list[dict[str, Any]] = []
        self.condition_rows: list[ConditionRow] = []

        self.dataset_var = tk.StringVar()
        self.count_var = tk.StringVar(value="1000")
        self.combine_var = tk.StringVar(value="and")
        self.strategy_var = tk.StringVar(value="linear")
        self.index_field_var = tk.StringVar(value="id")
        self.workers_var = tk.StringVar(value="2")
        self.status_var = tk.StringVar(value="Gotowe.")

        self.configure(bg="#f4f6f8")
        self.configure_style()
        self.build_layout()
        self.refresh_datasets()
        self.add_condition_row()

    def configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f6f8", foreground="#172033", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#172033", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#172033", font=("Segoe UI", 20, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def build_layout(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Wyszukiwanie wartosci w zbiorze danych", style="Title.TLabel").pack(anchor="w", pady=(0, 14))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        controls = ttk.Frame(body, style="Panel.TFrame", padding=14)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        content = ttk.Frame(body)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.build_controls(controls)
        self.build_tabs(content)
        ttk.Label(outer, textvariable=self.status_var).pack(fill="x", pady=(10, 0))

    def build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Dataset", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.dataset_combo = ttk.Combobox(parent, textvariable=self.dataset_var, state="readonly", width=38)
        self.dataset_combo.pack(fill="x", pady=(8, 6))

        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(0, 10))
        ttk.Button(row, text="Odswiez", command=self.refresh_datasets).pack(side="left")
        ttk.Button(row, text="Wczytaj", command=self.load_selected_dataset).pack(side="left", padx=(6, 0))

        ttk.Label(parent, text="Przygotuj dataset", style="Panel.TLabel").pack(anchor="w")
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(5, 14))
        ttk.Entry(row, textvariable=self.count_var, width=14).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Generuj/wczytaj", command=self.prepare_dataset).pack(side="left", padx=(6, 0))

        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Label(parent, text="Warunki", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        mode_row = ttk.Frame(parent, style="Panel.TFrame")
        mode_row.pack(fill="x", pady=(8, 6))
        ttk.Radiobutton(mode_row, text="AND", value="and", variable=self.combine_var).pack(side="left")
        ttk.Radiobutton(mode_row, text="OR", value="or", variable=self.combine_var).pack(side="left", padx=(10, 0))
        self.conditions_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.conditions_frame.pack(fill="x")
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(8, 14))
        ttk.Button(row, text="Dodaj warunek", command=self.add_condition_row).pack(side="left")
        ttk.Button(row, text="Usun ostatni", command=self.remove_condition_row).pack(side="left", padx=(6, 0))

        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Label(parent, text="Strategia", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Combobox(parent, textvariable=self.strategy_var, state="readonly", values=self.engine.available_strategies(), width=38).pack(fill="x", pady=(8, 6))
        ttk.Label(parent, text="Pole indeksu", style="Panel.TLabel").pack(anchor="w")
        ttk.Combobox(parent, textvariable=self.index_field_var, state="readonly", values=list(FIELDS), width=38).pack(fill="x", pady=(5, 6))
        ttk.Label(parent, text="Workery", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(parent, textvariable=self.workers_var, width=14).pack(anchor="w", pady=(5, 14))

        ttk.Button(parent, text="Szukaj", style="Accent.TButton", command=self.search).pack(fill="x", pady=(4, 6))
        ttk.Button(parent, text="Benchmark", command=self.run_benchmark).pack(fill="x", pady=6)
        ttk.Button(parent, text="Eksportuj CSV", command=self.export_results).pack(fill="x", pady=6)

    def build_tabs(self, parent: ttk.Frame) -> None:
        tabs = ttk.Notebook(parent)
        tabs.grid(row=0, column=0, sticky="nsew")
        results_tab = ttk.Frame(tabs, padding=10)
        benchmark_tab = ttk.Frame(tabs, padding=10)
        tabs.add(results_tab, text="Wyniki")
        tabs.add(benchmark_tab, text="Benchmark")

        results_tab.rowconfigure(0, weight=1)
        results_tab.columnconfigure(0, weight=1)
        columns = list(FIELDS)
        self.results_tree = ttk.Treeview(results_tab, columns=columns, show="headings")
        for column in columns:
            self.results_tree.heading(column, text=column)
            self.results_tree.column(column, width=110, minwidth=80, stretch=True)
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(results_tab, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")

        benchmark_tab.rowconfigure(0, weight=1)
        benchmark_tab.columnconfigure(0, weight=1)
        self.benchmark_text = tk.Text(benchmark_tab, font=("Consolas", 10), wrap="none", padx=10, pady=10)
        self.benchmark_text.grid(row=0, column=0, sticky="nsew")

    def refresh_datasets(self) -> None:
        names = [path.name for path in list_datasets()]
        self.dataset_combo.configure(values=names)
        if names and not self.dataset_var.get():
            self.dataset_var.set(names[0])
        self.status_var.set(f"Datasety: {len(names)}")

    def prepare_dataset(self) -> None:
        try:
            count = int(self.count_var.get())
        except ValueError:
            messagebox.showerror("Blad", "Liczba rekordow musi byc liczba calkowita.")
            return

        def task() -> Path:
            return ensure_dataset(count)

        def done(path: Path) -> None:
            self.refresh_datasets()
            self.dataset_var.set(path.name)
            self.load_selected_dataset()

        self.run_background("Przygotowywanie datasetu...", task, done)

    def load_selected_dataset(self) -> None:
        name = self.dataset_var.get()
        if not name:
            messagebox.showwarning("Dataset", "Najpierw wybierz dataset.")
            return
        path = list_datasets()[[p.name for p in list_datasets()].index(name)]

        def task() -> list[dict[str, Any]]:
            return load_dataset(path)

        def done(data: list[dict[str, Any]]) -> None:
            self.dataset_path = path
            self.data = data
            self.last_results = []
            self.populate_results([])
            self.status_var.set(f"Wczytano {path.name}: {len(data)} rekordow.")

        self.run_background("Wczytywanie datasetu...", task, done)

    def add_condition_row(self) -> None:
        row = ConditionRow(self.conditions_frame, self.update_row_operator)
        row.frame.pack(fill="x", pady=3)
        self.condition_rows.append(row)

    def remove_condition_row(self) -> None:
        if len(self.condition_rows) > 1:
            self.condition_rows.pop().frame.destroy()

    def update_row_operator(self, row: "ConditionRow") -> None:
        operators = OPERATORS_BY_TYPE[FIELDS[row.field_var.get()]]
        row.operator_combo.configure(values=operators)
        row.operator_var.set(operators[0])

    def parse_workers(self) -> int:
        workers = int(self.workers_var.get())
        max_workers = max(1, min(32, os.cpu_count() or 4))
        if workers <= 0 or workers > max_workers:
            raise ValueError(f"Workery musza byc w zakresie 1-{max_workers}. Dla duzych danych ustaw 2-8.")
        return workers

    def selected_condition(self):
        conditions = []
        for row in self.condition_rows:
            field_name = row.field_var.get()
            value = parse_value(field_name, row.value_var.get())
            conditions.append(build_condition(field_name, row.operator_var.get(), value))
        return combine_conditions(conditions, self.combine_var.get())

    def strategy_options(self) -> dict[str, Any]:
        strategy = self.strategy_var.get()
        options: dict[str, Any] = {}
        if strategy == "indexed":
            options["index_field"] = self.index_field_var.get()
        if strategy == "parallel":
            options["workers"] = self.parse_workers()
        return options

    def search(self) -> None:
        if not self.data:
            messagebox.showwarning("Dane", "Najpierw wczytaj dataset.")
            return
        try:
            condition = self.selected_condition()
            strategy = self.strategy_var.get()
            options = self.strategy_options()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))
            return

        def task() -> list[dict[str, Any]]:
            return self.engine.search(self.data, condition, strategy=strategy, **options)

        def done(results: list[dict[str, Any]]) -> None:
            self.last_results = results
            self.populate_results(results[:1000])
            self.status_var.set(f"Znaleziono {len(results)} rekordow. Pokazano maks. 1000.")

        self.run_background("Wyszukiwanie...", task, done)

    def run_benchmark(self) -> None:
        if not self.data:
            messagebox.showwarning("Dane", "Najpierw wczytaj dataset.")
            return
        try:
            workers = self.parse_workers()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))
            return

        def task() -> str:
            results = run_benchmark(self.data, workers=workers)
            path = save_benchmark(results, default_output_path("benchmark_results.csv"))
            lines = [f"Zapisano: {path}", ""]
            for result in results:
                status = "OK" if result.equals_linear else "ERROR"
                lines.append(
                    f"{status:5} | {result.case_name:<22} | {result.strategy:<8} | "
                    f"{result.elapsed_seconds:.6f}s | count={result.result_count}"
                )
            return "\n".join(lines)

        def done(text: str) -> None:
            self.benchmark_text.delete("1.0", "end")
            self.benchmark_text.insert("1.0", text)
            self.status_var.set("Benchmark zakonczony.")

        self.run_background("Uruchamianie benchmarku...", task, done)

    def export_results(self) -> None:
        if not self.last_results:
            messagebox.showwarning("Eksport", "Brak wynikow do zapisania.")
            return
        path = filedialog.asksaveasfilename(
            initialdir=default_output_path(".").parent,
            initialfile="search_results.csv",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            self.status_var.set(f"Zapisano: {save_records(self.last_results, path)}")

    def populate_results(self, records: list[dict[str, Any]]) -> None:
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        for record in records:
            self.results_tree.insert("", "end", values=[record.get(column, "") for column in FIELDS])

    def run_background(self, status: str, task: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        self.status_var.set(status)

        def worker() -> None:
            try:
                result = task()
            except Exception as exc:
                error = exc
                self.after(0, lambda error=error: self.show_error(error))
                return
            self.after(0, lambda result=result: on_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def show_error(self, exc: Exception) -> None:
        self.status_var.set("Wystapil blad.")
        messagebox.showerror("Blad", str(exc))


class ConditionRow:
    def __init__(self, parent: ttk.Frame, on_field_change: Callable[["ConditionRow"], None]) -> None:
        self.frame = ttk.Frame(parent, style="Panel.TFrame")
        self.field_var = tk.StringVar(value="city")
        self.operator_var = tk.StringVar(value="==")
        self.value_var = tk.StringVar(value="Warszawa")
        self.field_combo = ttk.Combobox(self.frame, textvariable=self.field_var, state="readonly", values=list(FIELDS), width=15)
        self.field_combo.pack(side="left", fill="x", expand=True)
        self.operator_combo = ttk.Combobox(self.frame, textvariable=self.operator_var, state="readonly", values=OPERATORS_BY_TYPE["str"], width=10)
        self.operator_combo.pack(side="left", padx=5)
        ttk.Entry(self.frame, textvariable=self.value_var, width=16).pack(side="left", fill="x", expand=True)
        self.field_combo.bind("<<ComboboxSelected>>", lambda _event: on_field_change(self))


def main() -> None:
    freeze_support()
    DesktopApp().mainloop()


if __name__ == "__main__":
    main()

