from __future__ import annotations

import os
import threading
import tkinter as tk
from multiprocessing import freeze_support
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from benchmark import (
    BenchmarkCase,
    default_cases,
    describe_case,
    load_benchmark_cases,
    run_benchmark,
    save_benchmark,
    save_benchmark_cases,
)
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
        self.minsize(760, 440)

        self.engine = SearchEngine()
        self.data: list[dict[str, Any]] = []
        self.dataset_path: Path | None = None
        self.last_results: list[dict[str, Any]] = []
        self.condition_rows: list[ConditionRow] = []
        self.benchmark_cases: list[BenchmarkCase] = []

        self.dataset_var = tk.StringVar()
        self.count_var = tk.StringVar(value="1000")
        self.combine_var = tk.StringVar(value="and")
        self.strategy_var = tk.StringVar(value="linear")
        self.index_field_var = tk.StringVar(value="id")
        self.workers_var = tk.StringVar(value="2")
        self.benchmark_name_var = tk.StringVar()
        self.benchmark_field_var = tk.StringVar(value="city")
        self.benchmark_operator_var = tk.StringVar(value="==")
        self.benchmark_value_var = tk.StringVar(value="Warszawa")
        self.benchmark_index_field_var = tk.StringVar(value="city")
        self.status_var = tk.StringVar(value="Gotowe.")

        self.configure(bg="#f4f6f8")
        self.configure_style()
        self.build_layout()
        self.load_benchmark_case_config()
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

        controls_host = ttk.Frame(body, style="Panel.TFrame")
        controls_host.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        controls_host.rowconfigure(0, weight=1)
        controls_host.columnconfigure(0, weight=1)
        controls_host.grid_propagate(False)
        controls_host.configure(width=330)

        self.controls_canvas = tk.Canvas(controls_host, bg="#ffffff", highlightthickness=0, width=330)
        controls_scroll = ttk.Scrollbar(controls_host, orient="vertical", command=self.controls_canvas.yview)
        self.controls_canvas.configure(yscrollcommand=controls_scroll.set)
        self.controls_canvas.grid(row=0, column=0, sticky="nsew")
        controls_scroll.grid(row=0, column=1, sticky="ns")

        controls = ttk.Frame(self.controls_canvas, style="Panel.TFrame", padding=14)
        controls_window = self.controls_canvas.create_window((0, 0), window=controls, anchor="nw")
        controls.bind(
            "<Configure>",
            lambda _event: self.controls_canvas.configure(scrollregion=self.controls_canvas.bbox("all")),
        )
        self.controls_canvas.bind(
            "<Configure>",
            lambda event: self.controls_canvas.itemconfigure(controls_window, width=event.width),
        )
        self.controls_canvas.bind("<Enter>", self.bind_control_scroll)
        self.controls_canvas.bind("<Leave>", self.unbind_control_scroll)
        controls.bind("<Enter>", self.bind_control_scroll)
        controls.bind("<Leave>", self.unbind_control_scroll)

        content = ttk.Frame(body)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.build_controls(controls)
        self.build_tabs(content)
        ttk.Label(outer, textvariable=self.status_var).pack(fill="x", pady=(10, 0))

    def bind_control_scroll(self, _event: tk.Event) -> None:
        self.controls_canvas.bind_all("<MouseWheel>", self.scroll_controls)

    def unbind_control_scroll(self, _event: tk.Event) -> None:
        self.controls_canvas.unbind_all("<MouseWheel>")

    def scroll_controls(self, event: tk.Event) -> None:
        self.controls_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def adjust_benchmark_form_layout(self, event: tk.Event) -> None:
        if not hasattr(self, "benchmark_case_form"):
            return

        compact = event.width < 900
        positions = {
            "label_nazwa": (0, 0),
            "input_nazwa": (0, 1),
            "label_pole": (0, 2),
            "input_pole": (0, 3),
            "label_operator": (0, 4),
            "input_operator": (0, 5),
            "label_wartosc": (1 if compact else 0, 0 if compact else 6),
            "input_wartosc": (1 if compact else 0, 1 if compact else 7),
            "label_indeks": (1 if compact else 0, 2 if compact else 8),
            "input_indeks": (1 if compact else 0, 3 if compact else 9),
            "button_save": (1 if compact else 0, 4 if compact else 10),
        }

        for name, widget in self.benchmark_form_widgets.items():
            row, column = positions[name]
            columnspan = 2 if compact and name == "button_save" else 1
            widget.grid_configure(row=row, column=column, columnspan=columnspan)

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
        ttk.Entry(parent, textvariable=self.workers_var, width=14).pack(anchor="w", pady=(5, 4))
        ttk.Label(
            parent,
            text="Liczba workerow jest brana pod uwage przy strategiach parallel i distributed.",
            style="Panel.TLabel",
            wraplength=280,
        ).pack(anchor="w", pady=(0, 14))

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
            self.results_tree.column(column, width=125, minwidth=90, stretch=False)
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(results_tab, orient="vertical", command=self.results_tree.yview)
        x_scroll = ttk.Scrollbar(results_tab, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        benchmark_tab.rowconfigure(1, weight=1)
        benchmark_tab.columnconfigure(0, weight=1)
        cases_frame = ttk.Frame(benchmark_tab)
        cases_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        cases_frame.columnconfigure(0, weight=1)

        ttk.Label(cases_frame, text="Scenariusze benchmarka", font=("Segoe UI", 10, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )
        self.benchmark_cases_tree = ttk.Treeview(
            cases_frame,
            columns=("name", "filters", "index_field"),
            show="headings",
            height=5,
        )
        self.benchmark_cases_tree.heading("name", text="nazwa")
        self.benchmark_cases_tree.heading("filters", text="warunki")
        self.benchmark_cases_tree.heading("index_field", text="indeks")
        self.benchmark_cases_tree.column("name", width=150, minwidth=100, stretch=True)
        self.benchmark_cases_tree.column("filters", width=420, minwidth=180, stretch=True)
        self.benchmark_cases_tree.column("index_field", width=90, minwidth=70, stretch=True)
        self.benchmark_cases_tree.grid(row=1, column=0, sticky="ew")
        self.benchmark_cases_tree.bind("<<TreeviewSelect>>", self.load_selected_benchmark_case_into_form)
        cases_scroll = ttk.Scrollbar(cases_frame, orient="vertical", command=self.benchmark_cases_tree.yview)
        self.benchmark_cases_tree.configure(yscrollcommand=cases_scroll.set)
        cases_scroll.grid(row=1, column=1, sticky="ns")

        self.benchmark_case_form = ttk.Frame(cases_frame)
        case_form = self.benchmark_case_form
        case_form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for column in range(11):
            case_form.columnconfigure(column, weight=0)
        for column in (1, 3, 5, 7, 9, 10):
            case_form.columnconfigure(column, weight=1)

        label_name = ttk.Label(case_form, text="Nazwa")
        label_name.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=3)
        input_name = ttk.Entry(case_form, textvariable=self.benchmark_name_var, width=14)
        input_name.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 10),
            pady=3,
        )
        label_field = ttk.Label(case_form, text="Pole")
        label_field.grid(row=0, column=2, sticky="w", padx=(0, 5), pady=3)
        self.benchmark_field_combo = ttk.Combobox(
            case_form,
            textvariable=self.benchmark_field_var,
            state="readonly",
            values=list(FIELDS),
            width=12,
        )
        self.benchmark_field_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=(0, 10),
            pady=3,
        )
        self.benchmark_field_combo.bind("<<ComboboxSelected>>", self.update_benchmark_operator)
        label_operator = ttk.Label(case_form, text="Operator")
        label_operator.grid(row=0, column=4, sticky="w", padx=(0, 5), pady=3)
        self.benchmark_operator_combo = ttk.Combobox(
            case_form,
            textvariable=self.benchmark_operator_var,
            state="readonly",
            values=OPERATORS_BY_TYPE["str"],
            width=8,
        )
        self.benchmark_operator_combo.grid(
            row=0,
            column=5,
            sticky="ew",
            padx=(0, 10),
            pady=3,
        )
        label_value = ttk.Label(case_form, text="Wartosc")
        label_value.grid(row=0, column=6, sticky="w", padx=(0, 5), pady=3)
        input_value = ttk.Entry(case_form, textvariable=self.benchmark_value_var, width=14)
        input_value.grid(
            row=0,
            column=7,
            sticky="ew",
            padx=(0, 10),
            pady=3,
        )
        label_index = ttk.Label(case_form, text="Indeks")
        label_index.grid(row=0, column=8, sticky="w", padx=(0, 5), pady=3)
        input_index = ttk.Combobox(
            case_form,
            textvariable=self.benchmark_index_field_var,
            state="readonly",
            values=list(FIELDS),
            width=12,
        )
        input_index.grid(row=0, column=9, sticky="ew", padx=(0, 10), pady=3)
        button_save = ttk.Button(case_form, text="Dodaj / aktualizuj", command=self.add_benchmark_case_from_form)
        button_save.grid(
            row=0,
            column=10,
            sticky="ew",
            pady=3,
        )
        self.benchmark_form_widgets = {
            "label_nazwa": label_name,
            "input_nazwa": input_name,
            "label_pole": label_field,
            "input_pole": self.benchmark_field_combo,
            "label_operator": label_operator,
            "input_operator": self.benchmark_operator_combo,
            "label_wartosc": label_value,
            "input_wartosc": input_value,
            "label_indeks": label_index,
            "input_indeks": input_index,
            "button_save": button_save,
        }

        case_buttons = ttk.Frame(cases_frame)
        case_buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(case_buttons, text="Usun", command=self.remove_selected_benchmark_case).pack(side="left")
        ttk.Button(case_buttons, text="Domyslne", command=self.reset_benchmark_cases).pack(side="left", padx=(6, 0))
        ttk.Button(case_buttons, text="Zapisz", command=self.save_benchmark_case_config).pack(side="left", padx=(6, 0))
        cases_frame.bind("<Configure>", self.adjust_benchmark_form_layout)

        self.benchmark_text = tk.Text(benchmark_tab, font=("Consolas", 10), wrap="none", padx=10, pady=10)
        self.benchmark_text.grid(row=1, column=0, sticky="nsew")
        benchmark_y_scroll = ttk.Scrollbar(benchmark_tab, orient="vertical", command=self.benchmark_text.yview)
        benchmark_x_scroll = ttk.Scrollbar(benchmark_tab, orient="horizontal", command=self.benchmark_text.xview)
        self.benchmark_text.configure(
            yscrollcommand=benchmark_y_scroll.set,
            xscrollcommand=benchmark_x_scroll.set,
        )
        benchmark_y_scroll.grid(row=1, column=1, sticky="ns")
        benchmark_x_scroll.grid(row=2, column=0, sticky="ew")

    def refresh_datasets(self) -> None:
        datasets = list_datasets()
        names = [path.name for path in datasets]
        selected = self.dataset_var.get()
        self.dataset_combo.configure(values=names)
        if names:
            self.dataset_var.set(selected if selected in names else names[0])
        else:
            self.dataset_var.set("")
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
        datasets = {path.name: path for path in list_datasets()}
        path = datasets.get(name)
        if path is None:
            self.refresh_datasets()
            messagebox.showwarning("Dataset", "Nie znaleziono wybranego pliku. Lista zostala odswiezona.")
            return

        def task() -> list[dict[str, Any]]:
            return load_dataset(path)

        def done(data: list[dict[str, Any]]) -> None:
            self.dataset_path = path
            self.data = data
            self.last_results = data
            self.populate_results(data[:1000])
            self.status_var.set(f"Wczytano {path.name}: {len(data)} rekordow. Pokazano pierwsze 1000.")

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

    def current_filter_specs(self) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        for row in self.condition_rows:
            field_name = row.field_var.get()
            value = parse_value(field_name, row.value_var.get())
            filters.append(
                {
                    "field": field_name,
                    "operator": row.operator_var.get(),
                    "value": value,
                }
            )
        return filters

    def selected_condition(self):
        conditions = []
        for filter_spec in self.current_filter_specs():
            conditions.append(
                build_condition(
                    str(filter_spec["field"]),
                    str(filter_spec["operator"]),
                    filter_spec["value"],
                )
            )
        return combine_conditions(conditions, self.combine_var.get())

    def strategy_options(self) -> dict[str, Any]:
        strategy = self.strategy_var.get()
        options: dict[str, Any] = {}
        if strategy == "indexed":
            options["index_field"] = self.index_field_var.get()
        if strategy in {"parallel", "distributed"}:
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

    def load_benchmark_case_config(self) -> None:
        try:
            self.benchmark_cases = load_benchmark_cases()
        except Exception as exc:
            self.benchmark_cases = default_cases()
            self.status_var.set(f"Nie wczytano konfiguracji benchmarka: {exc}")
        self.refresh_benchmark_cases_view()

    def save_benchmark_case_config(self) -> None:
        path = save_benchmark_cases(self.benchmark_cases)
        self.status_var.set(f"Zapisano scenariusze benchmarka: {path}")

    def refresh_benchmark_cases_view(self) -> None:
        if not hasattr(self, "benchmark_cases_tree"):
            return
        for item in self.benchmark_cases_tree.get_children():
            self.benchmark_cases_tree.delete(item)
        for case in self.benchmark_cases:
            self.benchmark_cases_tree.insert(
                "",
                "end",
                values=(case.name, describe_case(case), case.index_field),
            )

    def build_default_case_name(self, filters: list[dict[str, Any]]) -> str:
        operator_tokens = {
            "==": "eq",
            "!=": "ne",
            ">": "gt",
            ">=": "gte",
            "<": "lt",
            "<=": "lte",
            "contains": "contains",
        }
        parts = [
            f"{filter_spec['field']}_{operator_tokens.get(str(filter_spec['operator']), str(filter_spec['operator']))}_{filter_spec['value']}"
            for filter_spec in filters
        ]
        separator = f"_{self.combine_var.get()}_"
        return separator.join(str(part).lower().replace(" ", "_") for part in parts)

    def update_benchmark_operator(self, _event: tk.Event | None = None) -> None:
        field_name = self.benchmark_field_var.get()
        operators = OPERATORS_BY_TYPE[FIELDS[field_name]]
        self.benchmark_operator_combo.configure(values=operators)
        if self.benchmark_operator_var.get() not in operators:
            self.benchmark_operator_var.set(operators[0])
        self.benchmark_index_field_var.set(field_name)

    def benchmark_filter_specs(self) -> list[dict[str, Any]]:
        field_name = self.benchmark_field_var.get()
        return [
            {
                "field": field_name,
                "operator": self.benchmark_operator_var.get(),
                "value": parse_value(field_name, self.benchmark_value_var.get()),
            }
        ]

    def save_or_replace_benchmark_case(self, case: BenchmarkCase) -> None:
        for index, existing_case in enumerate(self.benchmark_cases):
            if existing_case.name == case.name:
                self.benchmark_cases[index] = case
                break
        else:
            self.benchmark_cases.append(case)

        self.refresh_benchmark_cases_view()
        self.save_benchmark_case_config()

    def add_benchmark_case_from_form(self) -> None:
        try:
            filters = self.benchmark_filter_specs()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))
            return

        name = self.benchmark_name_var.get().strip() or self.build_default_case_name(filters)
        case = BenchmarkCase(
            name=name,
            filters=tuple(filters),
            combine="and",
            index_field=self.benchmark_index_field_var.get() or str(filters[0]["field"]),
        )
        self.save_or_replace_benchmark_case(case)

    def load_selected_benchmark_case_into_form(self, _event: tk.Event | None = None) -> None:
        selected = self.benchmark_cases_tree.selection()
        if not selected:
            return

        values = self.benchmark_cases_tree.item(selected[0], "values")
        if not values:
            return

        selected_name = str(values[0])
        case = next((item for item in self.benchmark_cases if item.name == selected_name), None)
        if case is None:
            return

        self.benchmark_name_var.set(case.name)
        self.benchmark_index_field_var.set(case.index_field)
        if case.filters:
            filter_spec = case.filters[0]
            self.benchmark_field_var.set(str(filter_spec["field"]))
            self.update_benchmark_operator()
            self.benchmark_operator_var.set(str(filter_spec["operator"]))
            self.benchmark_value_var.set(str(filter_spec["value"]))
            self.benchmark_index_field_var.set(case.index_field)

    def add_benchmark_case_from_current(self) -> None:
        try:
            filters = self.current_filter_specs()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))
            return
        if not filters:
            messagebox.showwarning("Benchmark", "Brak warunkow do zapisania.")
            return

        name = self.benchmark_name_var.get().strip() or self.build_default_case_name(filters)
        case = BenchmarkCase(
            name=name,
            filters=tuple(filters),
            combine=self.combine_var.get(),
            index_field=self.index_field_var.get() or str(filters[0]["field"]),
        )

        self.benchmark_name_var.set("")
        self.save_or_replace_benchmark_case(case)

    def remove_selected_benchmark_case(self) -> None:
        selected = self.benchmark_cases_tree.selection()
        if not selected:
            messagebox.showwarning("Benchmark", "Zaznacz scenariusz do usuniecia.")
            return
        selected_names = {
            str(self.benchmark_cases_tree.item(item, "values")[0])
            for item in selected
        }
        self.benchmark_cases = [case for case in self.benchmark_cases if case.name not in selected_names]
        self.refresh_benchmark_cases_view()
        self.save_benchmark_case_config()

    def reset_benchmark_cases(self) -> None:
        self.benchmark_cases = default_cases()
        self.refresh_benchmark_cases_view()
        self.save_benchmark_case_config()

    def run_benchmark(self) -> None:
        if not self.data:
            messagebox.showwarning("Dane", "Najpierw wczytaj dataset.")
            return
        if not self.benchmark_cases:
            messagebox.showwarning("Benchmark", "Brak scenariuszy benchmarka.")
            return
        try:
            workers = self.parse_workers()
        except Exception as exc:
            messagebox.showerror("Blad", str(exc))
            return

        cases = list(self.benchmark_cases)

        def task() -> str:
            results = run_benchmark(self.data, workers=workers, cases=cases)
            path = save_benchmark(results, default_output_path("benchmark_results.csv"))
            descriptions = {case.name: describe_case(case) for case in cases}
            lines = [f"Zapisano: {path}", f"Scenariusze: {len(cases)}", ""]
            for result in results:
                status = "ERROR" if result.error_message else ("OK" if result.equals_linear else "ERROR")
                details = f" | {result.error_message}" if result.error_message else ""
                lines.append(
                    f"{status:5} | {result.case_name:<24} | {descriptions.get(result.case_name, ''):<55} | "
                    f"{result.strategy:<8} | "
                    f"{result.elapsed_seconds:.6f}s | count={result.result_count}{details}"
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
