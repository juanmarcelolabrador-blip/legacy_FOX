# -*- coding: utf-8 -*-
"""
sistema_legacy_fox.py
=====================
Prototipo de "Sistema Legacy" con aspecto de ERP Visual FoxPro MDI
(Windows 95/98), usando Tkinter nativo.

Incluye:
    * Ventana contenedora principal (MDI) con barra de menú clásica:
      Sistema, Inventarios, Facturación, Ctas. por Cobrar, Configuración, Ayuda.
    * Barra de herramientas horizontal con botones retro (raised/bd=2):
      [F2] Nuevo, [F3] Buscar, [F5] Modificar, [F10] Facturar, [Imprimir].
    * Barra de estado inferior:
      Empresa: BULONERA RADA TILLY S.R.L. | Usuario: ADMIN | VFP Runtime 9.0.
    * Grilla de Stock/Bulonería (estilo Grid de FoxPro).

Comunicación en tiempo real con el copiloto moderno mediante
"codigo_seleccionado.json": cada acción publica un "evento"
(seleccion / facturar / limpiar / no_encontrado) que el copiloto interpreta.
"""

import json
import os
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

# ---------------------------------------------------------------------------
# "Tabla DBF" simulada (lista de diccionarios tipo tabla)
# ---------------------------------------------------------------------------
CAMPOS_DBF = ["codigo", "descripcion", "medida", "stock", "precio", "equivalencia"]

PRODUCTOS = [
    {"codigo": "TOR-M6-25",   "descripcion": "TORNILLO HEXAGONAL G8.8", "medida": "M6 x 25 mm",     "stock": 1200, "precio": 85,   "equivalencia": '≈ 1/4" x 1"       ·  Sustituto: TOR-1/4-1'},
    {"codigo": "TOR-M8-40",   "descripcion": "TORNILLO HEXAGONAL G8.8", "medida": "M8 x 40 mm",     "stock": 850,  "precio": 150,  "equivalencia": '≈ 5/16" x 1.1/2"   ·  Sustituto: TOR-M8-45'},
    {"codigo": "TOR-M8-45",   "descripcion": "TORNILLO HEXAGONAL G8.8", "medida": "M8 x 45 mm",     "stock": 60,   "precio": 165,  "equivalencia": '≈ 5/16" x 1.3/4"   ·  Sustituto: TOR-M8-40'},
    {"codigo": "BUL-M12-60",  "descripcion": "BULÓN HEXAGONAL",         "medida": "M12 x 60 mm",    "stock": 340,  "precio": 520,  "equivalencia": '≈ 1/2" x 2.3/8"    ·  Sustituto: BUL-M12-70'},
    {"codigo": "TUE-M8",      "descripcion": "TUERCA HEXAGONAL",        "medida": "M8 (paso 1.25)", "stock": 5000, "precio": 45,   "equivalencia": '≈ 5/16" UNC       ·  Sustituto: TUE-5/16'},
    {"codigo": "ARA-M10",     "descripcion": "ARANDELA PLANA",          "medida": "M10 (Ø 10.5)",   "stock": 8000, "precio": 18,   "equivalencia": '≈ 3/8"            ·  DIN 125-A · Sustituto: ARA-3/8'},
    {"codigo": "GOL-M8",      "descripcion": "ARANDELA GROWER",         "medida": "M8 (Ø 8.2)",     "stock": 3000, "precio": 22,   "equivalencia": '≈ 5/16"           ·  DIN 127-B · Sustituto: GOL-5/16'},
    {"codigo": "ESP-M10-100", "descripcion": "ESPÁRRAGO ROSCADO",       "medida": "M10 x 100 mm",   "stock": 210,  "precio": 380,  "equivalencia": '≈ 3/8" x 4"       ·  Sustituto: ESP-M10-120'},
    {"codigo": "REM-4-8",     "descripcion": "REMACHE POP ALUMINIO",    "medida": "4 x 8 mm",       "stock": 1500, "precio": 35,   "equivalencia": '≈ 5/32" x 5/16"   ·  Sustituto: REM-4-10'},
    {"codigo": "VAR-M8-1000", "descripcion": "VARILLA ROSCADA",         "medida": "M8 x 1000 mm",   "stock": 95,   "precio": 1500, "equivalencia": '≈ 5/16" x 3.3 ft   ·  Sustituto: VAR-M10-1000'},
    {"codigo": "PRI-M6-30",   "descripcion": "PRISIONERO (ESPIGA)",     "medida": "M6 x 30 mm",     "stock": 460,  "precio": 110,  "equivalencia": '≈ 1/4" x 1.1/4"   ·  Sustituto: PRI-M6-40'},
    {"codigo": "KIT-BUL-100", "descripcion": "KIT BULONERÍA MIXTA",     "medida": "100 pzs (M6-M12)", "stock": 40, "precio": 2890, "equivalencia": "Tornillos, tuercas y arandelas · Sustituto: KIT-BUL-200"},
]

# Archivo JSON compartido con el copiloto moderno
RUTA_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codigo_seleccionado.json")
RUTA_JSON_COPILOTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precio_copiloto.json")
RUTA_CONTADOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contador_facturas.json")

# Paleta clásica Win95/98
FONDO = "#D4D0C8"
FONDO_OSCURO = "#C0C0C0"
BORDE_GRILLA = "#808080"
LINEA_GRILLA = "#C0C0C0"
SELECCION_BG = "#000080"
SELECCION_FG = "#FFFFFF"

# Datos de la empresa (barra de estado)
EMPRESA = "BULONERA RADA TILLY S.R.L."
USUARIO = "ADMIN"
RUNTIME = "VFP Runtime 9.0"

# Aumento simulado de precios (debe coincidir con el del copiloto)
AUMENTO_PORCENTAJE = 45

# IVA desglosado en el total de la venta (Argentina)
IVA_PORCENTAJE = 21


def formatear_precio(valor):
    """Formato es-CL/AR/ES: separador de miles con punto. 1500 -> 1.500"""
    return "{:,.0f}".format(int(valor)).replace(",", ".")


def generar_numero_comprobante():
    """Genera un número de comprobante único y secuencial (FAC-0001-00001024).

    Persiste el contador en disco para que la numeración sea continua entre
    sesiones; arranca en 1024 la primera vez.
    """
    secuencia = 1024
    try:
        with open(RUTA_CONTADOR, "r", encoding="utf-8") as f:
            secuencia = int(json.load(f).get("secuencia", secuencia))
    except Exception:
        secuencia = 1024

    numero = "FAC-0001-{:08d}".format(secuencia)

    try:
        with open(RUTA_CONTADOR, "w", encoding="utf-8") as f:
            json.dump({"secuencia": secuencia + 1}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return numero


def buscar_producto(codigo):
    """Búsqueda estilo FoxPro: primero exacta, luego por prefijo."""
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    for p in PRODUCTOS:
        if p["codigo"].upper() == codigo:
            return p
    for p in PRODUCTOS:
        if p["codigo"].upper().startswith(codigo):
            return p
    return None


class AppFox:
    """ERP legacy con aspecto Visual FoxPro MDI / Windows 95-98."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SISTEMA ERP LEGACY - " + EMPRESA + "  [Visual FoxPro MDI]")
        self.root.geometry("980x640")
        self.root.minsize(820, 540)
        self.root.configure(bg=FONDO)

        self._preparar_fuente()
        self.producto_actual = None
        self.celdas = []
        self.filas_frames = []

        self._construir_menu()
        self._construir_ui()
        self._vincular_teclas()

        self._actualizar_status()
        self.publicar({"codigo": ""}, evento="limpiar")

    # ------------------------------------------------------------- fuentes
    def _preparar_fuente(self):
        familias = set(tkfont.families(self.root))
        if "MS Sans Serif" in familias:
            self.fuente_familia = "MS Sans Serif"
        elif "Tahoma" in familias:
            self.fuente_familia = "Tahoma"
        else:
            self.fuente_familia = "Segoe UI"

    def fuente(self, sz=9, negrita=False):
        return (self.fuente_familia, sz, "bold") if negrita else (self.fuente_familia, sz)

    # --------------------------------------------------------------- menú
    def _construir_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        m_sis = tk.Menu(menubar, tearoff=0)
        m_sis.add_command(label="Salir", command=self.salir)
        m_sis.add_separator()
        m_sis.add_command(label="Acerca de...", command=self.acerca_de)
        menubar.add_cascade(label="Sistema", menu=m_sis)

        m_inv = tk.Menu(menubar, tearoff=0)
        m_inv.add_command(label="Artículos (Stock)", command=lambda: self._msg("Inventarios > Artículos"))
        m_inv.add_command(label="Movimientos de Stock", command=lambda: self._msg("Inventarios > Movimientos"))
        m_inv.add_separator()
        m_inv.add_command(label="Ajustes / Recuento", command=lambda: self._msg("Inventarios > Ajustes"))
        menubar.add_cascade(label="Inventarios", menu=m_inv)

        m_fac = tk.Menu(menubar, tearoff=0)
        m_fac.add_command(label="Nueva Factura", accelerator="F2", command=self.nuevo)
        m_fac.add_command(label="Facturar Selección", accelerator="F10", command=self.facturar)
        m_fac.add_separator()
        m_fac.add_command(label="Listado de Facturas", command=lambda: self._msg("Facturación > Listado"))
        menubar.add_cascade(label="Facturación", menu=m_fac)

        m_cxc = tk.Menu(menubar, tearoff=0)
        m_cxc.add_command(label="Clientes", command=lambda: self._msg("Ctas. por Cobrar > Clientes"))
        m_cxc.add_command(label="Cuentas Corrientes", command=lambda: self._msg("Ctas. por Cobrar > Cta. Cte."))
        menubar.add_cascade(label="Ctas. por Cobrar", menu=m_cxc)

        m_cfg = tk.Menu(menubar, tearoff=0)
        m_cfg.add_command(label="Parámetros Generales", command=lambda: self._msg("Configuración > Parámetros"))
        m_cfg.add_command(label="Usuarios y Permisos", command=lambda: self._msg("Configuración > Usuarios"))
        menubar.add_cascade(label="Configuración", menu=m_cfg)

        m_ayu = tk.Menu(menubar, tearoff=0)
        m_ayu.add_command(label="Contenido", command=lambda: self._msg("Ayuda > Contenido"))
        m_ayu.add_command(label="Acerca del Sistema", command=self.acerca_de)
        menubar.add_cascade(label="Ayuda", menu=m_ayu)

    # ---------------------------------------------------------- toolbar
    def _construir_toolbar(self):
        bar = tk.Frame(self.root, bg=FONDO, bd=1, relief="raised")
        bar.pack(fill="x", padx=6, pady=(6, 0))

        def btn(texto, cmd):
            return tk.Button(
                bar, text=texto, relief="raised", bd=2, font=self.fuente(9),
                command=cmd, bg=FONDO, activebackground=FONDO,
                cursor="hand2", highlightthickness=0, padx=8, pady=2)

        btn("[F2] Nuevo", self.nuevo).pack(side="left", padx=2)
        btn("[F3] Buscar", self.f3_buscar).pack(side="left", padx=2)
        btn("[F5] Modificar", self.modificar).pack(side="left", padx=2)
        btn("[F10] Facturar", self.facturar).pack(side="left", padx=2)
        btn("[Imprimir]", self.imprimir).pack(side="left", padx=2)

    # ------------------------------------------------------------ teclas
    def _vincular_teclas(self):
        self.root.bind("<F2>", lambda e: (self.nuevo(), "break")[1])
        self.root.bind("<F3>", lambda e: (self.f3_buscar(), "break")[1])
        self.root.bind("<F5>", lambda e: (self.modificar(), "break")[1])
        self.root.bind("<F10>", lambda e: (self.facturar(), "break")[1])
        self.root.bind("<Control-p>", lambda e: (self.imprimir(), "break")[1])
        self.root.bind("<Return>", self._on_enter)

    def _on_enter(self, event=None):
        w = self.root.focus_get()
        if w is self.entry_codigo:
            self.buscar()
        elif isinstance(w, tk.Button):
            return None
        elif self.producto_actual is not None:
            self.facturar()
        else:
            self.buscar()
        return "break"

    # --------------------------------------------------------------- UI
    def _construir_ui(self):
        # Barra de herramientas
        self._construir_toolbar()

        # Barra de búsqueda
        barra = tk.Frame(self.root, bg=FONDO)
        barra.pack(fill="x", padx=10, pady=(6, 0))

        tk.Label(barra, text="Código:", bg=FONDO, font=self.fuente(9)).pack(side="left")

        self.entry_codigo = tk.Entry(
            barra, relief="sunken", bd=2, font=self.fuente(10),
            bg="white", fg="black", width=22, insertbackground="black")
        self.entry_codigo.pack(side="left", padx=(4, 8))

        self.btn_buscar = tk.Button(
            barra, text="Buscar", relief="raised", bd=2, font=self.fuente(9),
            command=self.buscar, bg=FONDO, activebackground=FONDO,
            width=10, cursor="hand2", highlightthickness=0)
        self.btn_buscar.pack(side="left", padx=(0, 6))

        self.btn_limpiar = tk.Button(
            barra, text="Limpiar", relief="raised", bd=2, font=self.fuente(9),
            command=self.limpiar, bg=FONDO, activebackground=FONDO,
            width=10, cursor="hand2", highlightthickness=0)
        self.btn_limpiar.pack(side="left")

        # Grilla estilo Grid de FoxPro
        self._construir_grilla()

        # Barra de mensajes (estado de selección)
        self.status_var = tk.StringVar()
        msgbar = tk.Label(
            self.root, textvariable=self.status_var, relief="sunken", bd=2,
            anchor="w", bg=FONDO, fg="black", font=self.fuente(9), padx=4)
        msgbar.pack(side="bottom", fill="x", padx=6, pady=(0, 2))

        # Barra de estado inferior: Empresa | Usuario | Runtime
        status_frame = tk.Frame(self.root, bg=FONDO, bd=2, relief="sunken")
        status_frame.pack(side="bottom", fill="x", padx=6, pady=(0, 6))

        tk.Label(status_frame, text="Empresa: " + EMPRESA, bg=FONDO, fg="black",
                 font=self.fuente(9), anchor="w").pack(side="left", padx=(6, 0))
        tk.Label(status_frame, text="|", bg=FONDO, fg="black",
                 font=self.fuente(9)).pack(side="left", padx=(8, 0))
        tk.Label(status_frame, text="Usuario: " + USUARIO, bg=FONDO, fg="black",
                 font=self.fuente(9), anchor="w").pack(side="left", padx=(8, 0))
        tk.Label(status_frame, text="|", bg=FONDO, fg="black",
                 font=self.fuente(9)).pack(side="left", padx=(8, 0))
        tk.Label(status_frame, text=RUNTIME, bg=FONDO, fg="black",
                 font=self.fuente(9), anchor="e").pack(side="left", padx=(8, 6))

    def _construir_grilla(self):
        columnas = [
            ("CÓDIGO",       16, "w"),
            ("DESCRIPCIÓN",  26, "w"),
            ("MEDIDA",       16, "w"),
            ("STOCK",         8, "e"),
            ("PRECIO",       12, "e"),
        ]

        borde = tk.Frame(self.root, bg=BORDE_GRILLA, bd=0)
        borde.pack(fill="both", expand=True, padx=10, pady=(6, 4))
        interior = tk.Frame(borde, bg=LINEA_GRILLA, bd=0)
        interior.pack(fill="both", expand=True, padx=1, pady=1)

        for c, (titulo, ancho, ancla) in enumerate(columnas):
            interior.columnconfigure(c, weight=ancho)
            cont = tk.Frame(interior, bg=LINEA_GRILLA)
            cont.grid(row=0, column=c, sticky="nsew")
            lbl = tk.Label(
                cont, text=titulo, bg=FONDO_OSCURO, fg="black",
                relief="raised", bd=1, anchor="center",
                font=self.fuente(9, True), padx=4, pady=2)
            lbl.pack(fill="both", expand=True, padx=1, pady=1)

        for r, prod in enumerate(PRODUCTOS):
            fila_labels = []
            fila_frames = []
            for c, (titulo, ancho, ancla) in enumerate(columnas):
                campo = CAMPOS_DBF[c]
                if campo == "precio":
                    texto = "$" + formatear_precio(prod["precio"])
                elif campo == "stock":
                    texto = str(prod["stock"])
                else:
                    texto = str(prod[campo])

                cell = tk.Frame(interior, bg=LINEA_GRILLA)
                cell.grid(row=r + 1, column=c, sticky="nsew")
                lbl = tk.Label(
                    cell, text=texto, bg="white", fg="black",
                    anchor=ancla, font=self.fuente(9), padx=4, pady=1)
                lbl.pack(fill="both", expand=True, padx=1, pady=1)

                for w in (cell, lbl):
                    w.bind("<Button-1>", lambda e, idx=r: self._seleccionar(idx))
                    w.bind("<Double-Button-1>", lambda e, idx=r: self._doble_clic(idx))

                fila_labels.append(lbl)
                fila_frames.append(cell)
            self.celdas.append(fila_labels)
            self.filas_frames.append(fila_frames)

    # ---------------------------------------------------------- selección
    def _pintar_fila(self, idx, activa):
        if 0 <= idx < len(self.celdas):
            bg = SELECCION_BG if activa else "white"
            fg = SELECCION_FG if activa else "black"
            for lbl in self.celdas[idx]:
                lbl.configure(bg=bg, fg=fg)

    def _limpiar_seleccion(self):
        for i in range(len(self.celdas)):
            self._pintar_fila(i, False)

    def _seleccionar(self, idx):
        self._limpiar_seleccion()
        self._pintar_fila(idx, True)
        self.producto_actual = PRODUCTOS[idx]
        self.entry_codigo.delete(0, tk.END)
        self.entry_codigo.insert(0, PRODUCTOS[idx]["codigo"])
        self._actualizar_status()
        self.publicar(PRODUCTOS[idx], evento="seleccion")
        self.root.focus_set()

    def _doble_clic(self, idx):
        """Doble clic en la grilla: selecciona y abre la facturación."""
        self._seleccionar(idx)
        self.facturar()

    # ------------------------------------------------------------ acciones
    def buscar(self):
        codigo = self.entry_codigo.get()
        prod = buscar_producto(codigo)
        if prod is None:
            self._limpiar_seleccion()
            self.producto_actual = None
            self._actualizar_status("Código no encontrado: " + (codigo or "(vacío)"))
            self.publicar({"codigo": (codigo or "").strip().upper()}, evento="no_encontrado")
            messagebox.showwarning(
                "Buscar", "Código no encontrado:\n\n" + (codigo or "(vacío)"),
                parent=self.root)
            return
        idx = PRODUCTOS.index(prod)
        self._seleccionar(idx)

    def limpiar(self):
        self.entry_codigo.delete(0, tk.END)
        self._limpiar_seleccion()
        self.producto_actual = None
        self._actualizar_status()
        self.publicar({"codigo": ""}, evento="limpiar")

    def facturar(self):
        """Abre la ventana modal de facturación (punto de venta)."""
        if self.producto_actual is None:
            messagebox.showinfo(
                "Facturar", "Seleccione un artículo antes de facturar.", parent=self.root)
            return
        p = self.producto_actual
        # Notifica al copiloto que se inyectará el precio actualizado
        self.publicar(p, evento="facturar")
        self._abrir_factura(p)

    def _obtener_precio_copiloto(self, codigo, precio_viejo):
        """Lee el precio actualizado que publica el copiloto (con fallback local)."""
        try:
            with open(RUTA_JSON_COPILOTO, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if datos.get("codigo") == codigo and datos.get("precio_nuevo") is not None:
                return int(datos["precio_nuevo"])
        except Exception:
            pass
        # Fallback local: misma fórmula que el copiloto (+45%)
        return int(round(precio_viejo * (1.0 + AUMENTO_PORCENTAJE / 100.0)))

    def _abrir_factura(self, producto):
        """Ventana emergente modal multi-producto (estética Win95/FoxPro).

        Permite cargar varios ítems a una lista antes de facturar; cada ítem
        conserva el precio actualizado inyectado por el Copiloto. Al finalizar
        se guarda el array completo de ítems en codigo_seleccionado.json.
        """
        items = []  # lista de dicts: codigo, descripcion, cantidad, precio_unitario

        top = tk.Toplevel(self.root)
        top.title("Facturación - Punto de Venta")
        top.configure(bg=FONDO)
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        top.update_idletasks()
        w, h = 580, 500
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        top.geometry(f"{w}x{h}+{x}+{y}")

        # --- Variables del formulario del ítem actual ---
        var_codigo = tk.StringVar()
        var_desc = tk.StringVar()
        var_precio = tk.StringVar()
        var_cantidad = tk.StringVar(value="1")
        var_total = tk.StringVar(value="$0")

        def cargar_producto(prod):
            """Rellena el formulario con un producto y su precio de copiloto."""
            var_codigo.set(prod["codigo"])
            var_desc.set(prod["descripcion"])
            precio_nuevo = self._obtener_precio_copiloto(prod["codigo"], int(prod["precio"]))
            var_precio.set(str(precio_nuevo))
            var_cantidad.set("1")
            # Avisa al copiloto para que inyecte/muestre el precio actualizado
            self.publicar(prod, evento="facturar")

        def recalcular(*args):
            try:
                p = float(var_precio.get())
            except ValueError:
                p = 0.0
            try:
                c = float(var_cantidad.get())
            except ValueError:
                c = 0.0
            var_total.set("$" + formatear_precio(int(round(p * c))))

        var_precio.trace_add("write", recalcular)
        var_cantidad.trace_add("write", recalcular)

        # --- Formulario (retro FoxPro) ---
        form = tk.Frame(top, bg=FONDO)
        form.pack(fill="x", padx=12, pady=(12, 6))

        def fila(r, etiqueta, widget):
            tk.Label(form, text=etiqueta + ":", bg=FONDO, font=self.fuente(9),
                     anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=3)
            widget.grid(row=r, column=1, sticky="w", pady=3)

        e_codigo = tk.Entry(form, relief="sunken", bd=2, font=self.fuente(10),
                            bg="white", textvariable=var_codigo, width=30)
        fila(0, "Código", e_codigo)

        e_desc = tk.Entry(form, relief="sunken", bd=2, font=self.fuente(10),
                          bg="white", textvariable=var_desc, width=30,
                          readonlybackground="white")
        e_desc.configure(state="readonly")
        fila(1, "Descripción", e_desc)

        e_precio = tk.Entry(form, relief="sunken", bd=2, font=self.fuente(10),
                            bg="white", textvariable=var_precio, width=30)
        fila(2, "Precio Unitario", e_precio)

        e_cantidad = tk.Entry(form, relief="sunken", bd=2, font=self.fuente(10),
                              bg="white", textvariable=var_cantidad, width=30)
        fila(3, "Cantidad", e_cantidad)

        tk.Label(form, text="Total ítem:", bg=FONDO, font=self.fuente(9, True),
                 anchor="w").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=3)
        tk.Label(form, textvariable=var_total, bg=FONDO, fg="#000080",
                 font=self.fuente(11, True), anchor="w").grid(
            row=4, column=1, sticky="w", pady=3)

        def buscar_y_cargar():
            codigo = var_codigo.get().strip()
            prod = buscar_producto(codigo)
            if prod is None:
                messagebox.showwarning(
                    "Facturación", "Código no encontrado: " + (codigo or "(vacío)"),
                    parent=top)
                return
            cargar_producto(prod)
            e_cantidad.focus_set()
            e_cantidad.select_range(0, tk.END)

        # --- Lista de ítems cargados ---
        lista_frame = tk.Frame(top, bg=FONDO)
        lista_frame.pack(fill="both", expand=True, padx=12, pady=(6, 0))

        tk.Label(lista_frame, text="Ítems cargados (código · descripción · cantidad × precio):",
                 bg=FONDO, font=self.fuente(9, True), anchor="w").pack(fill="x")

        listbox = tk.Listbox(lista_frame, relief="sunken", bd=2, font=self.fuente(9),
                             bg="white", height=8, activestyle="dotbox",
                             selectbackground=SELECCION_BG, selectforeground=SELECCION_FG)
        scroll = tk.Scrollbar(lista_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scroll.set)
        listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        lbl_total_lista = tk.Label(
            top, text="Ítems: 0    Subtotal: $0    IVA 21%: $0    TOTAL: $0",
            bg=FONDO, fg="#000080", font=self.fuente(9, True), anchor="w")
        lbl_total_lista.pack(fill="x", padx=12, pady=(4, 0))

        def actualizar_total_lista():
            subtotal = sum(it["cantidad"] * it["precio_unitario"] for it in items)
            iva = int(round(subtotal * IVA_PORCENTAJE / 100.0))
            total = subtotal + iva
            lbl_total_lista.configure(
                text="Ítems: {}    Subtotal: ${}    IVA 21%: ${}    TOTAL: ${}".format(
                    len(items), formatear_precio(subtotal),
                    formatear_precio(iva), formatear_precio(total)))

        def agregar_item():
            codigo = var_codigo.get().strip().upper()
            if not codigo:
                messagebox.showwarning(
                    "Facturación", "Ingrese un código para agregar el ítem.", parent=top)
                return
            prod = buscar_producto(codigo)
            descripcion = var_desc.get().strip()
            if prod is not None:
                descripcion = prod["descripcion"]
            if not descripcion:
                messagebox.showwarning(
                    "Facturación", "Código no encontrado: " + codigo, parent=top)
                return
            try:
                precio = int(round(float(var_precio.get())))
            except ValueError:
                messagebox.showwarning("Facturación", "Precio inválido.", parent=top)
                return
            try:
                cantidad = int(float(var_cantidad.get()))
            except ValueError:
                messagebox.showwarning("Facturación", "Cantidad inválida.", parent=top)
                return
            if cantidad <= 0 or precio < 0:
                messagebox.showwarning(
                    "Facturación", "Ingrese una cantidad mayor a cero.", parent=top)
                return

            # Cada ítem conserva el precio actualizado inyectado por el Copiloto
            if prod is not None:
                precio = self._obtener_precio_copiloto(prod["codigo"], int(prod["precio"]))

            item = {
                "codigo": codigo,
                "descripcion": descripcion,
                "cantidad": cantidad,
                "precio_unitario": precio,
            }
            items.append(item)
            listbox.insert(
                tk.END,
                "{:<14} {:<26} {:>4} × ${}".format(
                    item["codigo"], item["descripcion"][:26],
                    item["cantidad"], formatear_precio(item["precio_unitario"])))

            # Limpiar el formulario para el próximo ítem
            var_codigo.set("")
            var_desc.set("")
            var_precio.set("")
            var_cantidad.set("1")
            var_total.set("$0")
            actualizar_total_lista()
            e_codigo.focus_set()

        def finalizar():
            if not items:
                messagebox.showwarning(
                    "Facturación", "Agregue al menos un ítem antes de facturar.", parent=top)
                return

            comprobante = generar_numero_comprobante()

            imprimir = messagebox.askyesno(
                "Imprimir Factura",
                "¿Desea imprimir la factura en la tiquetera física?\n\n"
                "Comprobante: " + comprobante,
                parent=top)
            if imprimir:
                self._actualizar_status("Imprimiendo factura en tiquetera física...")
                messagebox.showinfo(
                    "Impresión",
                    "Factura enviada a la tiquetera física.\n\n"
                    "Comprobante: " + comprobante,
                    parent=top)

            # Guarda el array completo de ítems (codigo, descripcion, cantidad,
            # precio_unitario) en codigo_seleccionado.json.
            self.publicar_venta_multi(items, comprobante)

            subtotal = sum(it["cantidad"] * it["precio_unitario"] for it in items)
            self._actualizar_status(
                "Venta facturada [{}]: {} ítem(s) = ${}".format(
                    comprobante, len(items), formatear_precio(subtotal)))
            top.destroy()

        def cancelar():
            self._actualizar_status("Facturación cancelada.")
            top.destroy()

        # --- Botones retro ---
        botones = tk.Frame(top, bg=FONDO)
        botones.pack(fill="x", padx=12, pady=(8, 12))

        tk.Button(botones, text="[ + Agregar Ítem ]", relief="raised", bd=2,
                  font=self.fuente(9), command=agregar_item, bg=FONDO,
                  activebackground=FONDO, width=18, cursor="hand2").pack(
            side="left", padx=6)
        tk.Button(botones, text="[ Finalizar / Facturar ]", relief="raised", bd=2,
                  font=self.fuente(9), command=finalizar, bg=FONDO,
                  activebackground=FONDO, width=22, cursor="hand2").pack(
            side="left", padx=6)
        tk.Button(botones, text="[ Cancelar ]", relief="raised", bd=2,
                  font=self.fuente(9), command=cancelar, bg=FONDO,
                  activebackground=FONDO, width=14, cursor="hand2").pack(
            side="left", padx=6)

        # Cargar el producto seleccionado como ítem inicial sugerido
        cargar_producto(producto)

        e_codigo.bind("<Return>", lambda e: buscar_y_cargar())
        e_cantidad.bind("<Return>", lambda e: agregar_item())
        top.bind("<Escape>", lambda e: cancelar())
        top.protocol("WM_DELETE_WINDOW", cancelar)

    def nuevo(self):
        self.limpiar()
        self.entry_codigo.focus_set()
        self._actualizar_status("Nuevo artículo (modo alta) - complete el código")

    def f3_buscar(self):
        self.entry_codigo.focus_set()
        self.entry_codigo.select_range(0, tk.END)
        self._actualizar_status("Ingrese el código a buscar...")

    def modificar(self):
        if self.producto_actual is None:
            self._msg("Seleccione un artículo para modificar.")
            return
        self._actualizar_status(
            "Modificando: {} - {}".format(
                self.producto_actual["codigo"], self.producto_actual["descripcion"]))
        self.entry_codigo.focus_set()

    def imprimir(self):
        self._actualizar_status(
            "Imprimiendo listado de Stock ({} registros)...".format(len(PRODUCTOS)))
        messagebox.showinfo(
            "Imprimir",
            "Enviando listado de stock a la impresora...\n\n(Vista previa simulada)",
            parent=self.root)

    def acerca_de(self):
        messagebox.showinfo(
            "Acerca de",
            "SISTEMA ERP LEGACY\nVisual FoxPro MDI (simulación)\n\n"
            "Empresa: " + EMPRESA + "\nUsuario: " + USUARIO + "\n" + RUNTIME,
            parent=self.root)

    def _msg(self, texto):
        self._actualizar_status(texto)

    def salir(self):
        self.root.destroy()

    # --------------------------------------------------- estado / JSON
    def _actualizar_status(self, extra=None):
        if extra is not None:
            self.status_var.set(extra)
        elif self.producto_actual is not None:
            self.status_var.set(
                "{} registros  ·  Seleccionado: {} - {}".format(
                    len(PRODUCTOS),
                    self.producto_actual["codigo"],
                    self.producto_actual["descripcion"]))
        else:
            self.status_var.set("{} registros".format(len(PRODUCTOS)))

    def _escribir_json(self, datos):
        datos["timestamp"] = time.strftime("%d/%m/%Y %H:%M:%S")
        datos["ts"] = time.time()
        try:
            with open(RUTA_JSON, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def publicar(self, producto, evento="seleccion"):
        """Escribe la selección/evento actual al JSON que lee el copiloto."""
        datos = dict(producto)
        datos["evento"] = evento
        self._escribir_json(datos)

    def publicar_venta(self, producto, cantidad, precio_unitario, total, comprobante):
        """Guarda la venta realizada marcándola con estado 'facturado'."""
        datos = dict(producto)
        datos["estado"] = "facturado"
        datos["evento"] = "facturado"
        datos["cantidad"] = cantidad
        datos["precio_unitario"] = precio_unitario
        datos["total"] = total
        datos["comprobante"] = comprobante
        datos["fecha"] = time.strftime("%d/%m/%Y")
        datos["hora"] = time.strftime("%H:%M:%S")
        self._escribir_json(datos)

    def publicar_venta_multi(self, items, comprobante):
        """Guarda la venta multi-producto marcándola con estado 'facturado'.

        Escribe el array completo de ítems (codigo, descripcion, cantidad,
        precio_unitario) en codigo_seleccionado.json para que el copiloto
        moderno genere la factura calculando Subtotal, IVA 21% y Total.
        """
        subtotal = sum(int(it["cantidad"]) * int(it["precio_unitario"]) for it in items)
        datos = {
            "estado": "facturado",
            "evento": "facturado",
            "items": items,
            "codigo": items[0]["codigo"],
            "descripcion": items[0]["descripcion"],
            "cantidad": items[0]["cantidad"],
            "precio_unitario": items[0]["precio_unitario"],
            "total": subtotal,
            "comprobante": comprobante,
            "fecha": time.strftime("%d/%m/%Y"),
            "hora": time.strftime("%H:%M:%S"),
        }
        self._escribir_json(datos)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AppFox().run()
