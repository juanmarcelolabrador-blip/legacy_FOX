# -*- coding: utf-8 -*-
"""
copiloto_jml_moderno.py
=======================
Ventana flotante MODERNA (customtkinter, modo oscuro #1E1E1E, bordes
redondeados, tipografía vectorial limpia) que lee EN PARALELO los eventos del
sistema legacy (sistema_legacy_fox.py) a través del archivo JSON compartido
"codigo_seleccionado.json".

Funcionalidades:
    * PRECIO ACTUALIZADO en verde grande + comparación con el precio viejo.
    * Notificación animada "Inyectando Precio Actualizado" al facturar (Enter).
    * Simulador de envío digital: botón "Enviar Comprobante por WhatsApp/Email".
"""

import json
import os
import time
import webbrowser

try:
    import customtkinter as ctk
    CTK_DISPONIBLE = True
except Exception:
    CTK_DISPONIBLE = False

try:
    import reportlab  # noqa: F401  (control de disponibilidad)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
    REPORTLAB_DISPONIBLE = True
except Exception:
    REPORTLAB_DISPONIBLE = False

# Archivo JSON compartido (misma carpeta que este script)
RUTA_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codigo_seleccionado.json")
RUTA_JSON_COPILOTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precio_copiloto.json")

# Paleta modo oscuro
COLOR_FONDO = "#1E1E1E"
COLOR_TARJETA = "#2B2B2B"
COLOR_BORDE = "#3A3A3A"
COLOR_TEXTO = "#F5F5F5"
COLOR_SECUNDARIO = "#9A9A9A"
COLOR_ACENTO = "#38BDF8"
COLOR_PRECIO = "#4ADE80"
COLOR_ALERTA = "#FB923C"      # naranja: desactualización
COLOR_NOTIF = "#22D3EE"       # cyan: notificación de inyección
COLOR_NOTIF_BG = "#0E2A33"
COLOR_OK_BG = "#0E2A1E"       # verde oscuro: venta facturada

FUENTE = "Segoe UI"

# Simulación de aumento de precios sobre el sistema viejo (FoxPro)
AUMENTO_PORCENTAJE = 45

# Cliente demo para la simulación de envío digital
CLIENTE_DEMO = "CONSTRUCTORA DEL SUR S.A."

# IVA desglosado en el comprobante digital (Argentina)
IVA_PORCENTAJE = 21

# Pasos de la simulación de envío de comprobante (texto, progreso)
PASOS_ENVIO = [
    ("✔ factura_actualizada.pdf generado y abierto", 0.30),
    ("Abriendo enlace de WhatsApp Web (wa.me)...", 0.60),
    ("Enviando resumen de factura al cliente...", 0.85),
    ("✔ Comprobante enviado por WhatsApp / Email", 1.0),
]


def leer_seleccion():
    """Lee el JSON compartido que escribe el sistema legacy."""
    try:
        with open(RUTA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def formatear_precio(valor):
    """Formato es-CL/AR/ES: separador de miles con punto. 1500 -> 1.500"""
    return "{:,.0f}".format(int(valor)).replace(",", ".")


def formatear_monto(valor):
    """Formato monetario AR con 2 decimales: 1234.5 -> '1.234,50'."""
    return "{:,.2f}".format(valor).replace(",", " ").replace(".", ",").replace(" ", ".")


class CopilotoJML:
    """Panel flotante moderno que acompaña al sistema legacy."""

    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("COPILOTO JML")
        self.root.configure(fg_color=COLOR_FONDO)
        self.root.resizable(True, True)
        self.root.minsize(380, 560)
        self.root.attributes("-topmost", True)

        ancho, alto = 460, 620
        x = self.root.winfo_screenwidth() - ancho - 40
        y = 50
        self.root.geometry(f"{ancho}x{alto}+{x}+{y}")

        self._ultimo_ts = None
        self._precio_nuevo = None
        self._codigo_actual = None
        self._pulso_activo = 0
        self._facturado = False
        self._cantidad_venta = 1
        self._total_venta = 0
        self._descripcion_actual = ""
        self._medida_actual = ""
        self._comprobante_actual = ""
        self._fecha_venta = ""
        self._hora_venta = ""
        self._items = []

        self._construir_ui()
        self.root.bind("<Configure>", self._ajustar_wraplength)
        self._refrescar()
        self._poll()

    def _construir_ui(self):
        # --- Encabezado ---
        header = ctk.CTkFrame(self.root, fg_color=COLOR_FONDO, corner_radius=0)
        header.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkLabel(header, text="COPILOTO JML", font=(FUENTE, 19, "bold"),
                     text_color=COLOR_TEXTO).pack(side="left")
        ctk.CTkLabel(header, text="● EN LÍNEA", font=(FUENTE, 11, "bold"),
                     text_color=COLOR_PRECIO).pack(side="right")

        # --- Banner de notificación (inyección de precio) ---
        self.banner_notif = ctk.CTkFrame(
            self.root, fg_color=COLOR_FONDO, corner_radius=10,
            border_width=1, border_color=COLOR_FONDO)
        self.banner_notif.pack(fill="x", padx=18, pady=(0, 6))
        self.lbl_notif = ctk.CTkLabel(
            self.banner_notif, text=" ", font=(FUENTE, 12, "bold"),
            text_color=COLOR_NOTIF, anchor="w", justify="left", wraplength=380)
        self.lbl_notif.pack(fill="x", padx=12, pady=(6, 6))

        # --- Tarjeta: código seleccionado ---
        card_codigo = ctk.CTkFrame(self.root, fg_color=COLOR_TARJETA, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDE)
        card_codigo.pack(fill="x", padx=18, pady=(4, 8))
        ctk.CTkLabel(card_codigo, text="CÓDIGO SELECCIONADO", font=(FUENTE, 11, "bold"),
                     text_color=COLOR_SECUNDARIO).pack(anchor="w", padx=16, pady=(12, 0))
        self.lbl_codigo = ctk.CTkLabel(card_codigo, text="—", font=(FUENTE, 22, "bold"),
                                       text_color=COLOR_ACENTO)
        self.lbl_codigo.pack(anchor="w", padx=16, pady=(2, 4))
        self.lbl_desc = ctk.CTkLabel(card_codigo, text="Esperando selección...",
                                     font=(FUENTE, 12), text_color=COLOR_SECUNDARIO)
        self.lbl_desc.pack(anchor="w", padx=16, pady=(0, 12))

        # --- Tarjeta: precio actualizado ---
        card_precio = ctk.CTkFrame(self.root, fg_color=COLOR_TARJETA, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDE)
        card_precio.pack(fill="x", padx=18, pady=(0, 8))
        ctk.CTkLabel(card_precio, text="PRECIO ACTUALIZADO", font=(FUENTE, 11, "bold"),
                     text_color=COLOR_SECUNDARIO).pack(anchor="w", padx=16, pady=(12, 0))
        self.lbl_precio = ctk.CTkLabel(card_precio, text="$ —", font=(FUENTE, 34, "bold"),
                                       text_color=COLOR_PRECIO)
        self.lbl_precio.pack(anchor="w", padx=16, pady=(2, 2))
        self.lbl_foxpro = ctk.CTkLabel(card_precio, text="", font=(FUENTE, 13, "bold"),
                                       text_color=COLOR_ALERTA)
        self.lbl_foxpro.pack(anchor="w", padx=16, pady=(0, 2))
        self.lbl_medida = ctk.CTkLabel(card_precio, text="", font=(FUENTE, 12),
                                       text_color=COLOR_SECUNDARIO)
        self.lbl_medida.pack(anchor="w", padx=16, pady=(0, 12))

        # --- Tarjeta: equivalencia de medida / stock ---
        card_eq = ctk.CTkFrame(self.root, fg_color=COLOR_TARJETA, corner_radius=14,
                               border_width=1, border_color=COLOR_BORDE)
        card_eq.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        ctk.CTkLabel(card_eq, text="EQUIVALENCIA DE MEDIDA / STOCK",
                     font=(FUENTE, 11, "bold"),
                     text_color=COLOR_SECUNDARIO).pack(anchor="w", padx=16, pady=(12, 0))
        self.lbl_eq = ctk.CTkLabel(card_eq, text="—", font=(FUENTE, 13),
                                   text_color=COLOR_TEXTO, wraplength=356,
                                   justify="left")
        self.lbl_eq.pack(anchor="w", padx=16, pady=(6, 4))
        self.lbl_stock = ctk.CTkLabel(card_eq, text="", font=(FUENTE, 12),
                                      text_color=COLOR_SECUNDARIO)
        self.lbl_stock.pack(anchor="w", padx=16, pady=(0, 12))

        # --- Botón destacado de envío digital ---
        self.btn_enviar = ctk.CTkButton(
            self.root, text="Enviar Comprobante por WhatsApp / Email",
            height=44, corner_radius=12, font=(FUENTE, 13, "bold"),
            fg_color="#25D366", hover_color="#1EBE5A", text_color="#062B12",
            state="disabled", command=self._simular_envio)
        self.btn_enviar.pack(fill="x", padx=18, pady=(0, 6))

        # --- Pie ---
        footer = ctk.CTkFrame(self.root, fg_color=COLOR_FONDO, corner_radius=0)
        footer.pack(fill="x", padx=18, pady=(6, 16))
        self.lbl_status = ctk.CTkLabel(footer, text="Sincronizando...",
                                       font=(FUENTE, 11), text_color=COLOR_SECUNDARIO)
        self.lbl_status.pack(side="left", pady=(4, 0))
        ctk.CTkButton(footer, text="Sincronizar", width=110, height=30, corner_radius=8,
                      fg_color="#333333", hover_color="#444444", font=(FUENTE, 12),
                      text_color=COLOR_TEXTO, command=self._refrescar).pack(side="right")

    def _ajustar_wraplength(self, event):
        """Reajusta el ancho del texto de equivalencia al redimensionar."""
        if event.widget is self.root and hasattr(self, "lbl_eq"):
            self.lbl_eq.configure(wraplength=max(180, event.width - 80))

    def _calcular_impacto(self, precio_viejo):
        """Aplica el aumento simulado y calcula el % de desactualización."""
        factor = 1.0 + AUMENTO_PORCENTAJE / 100.0
        precio_nuevo = int(round(precio_viejo * factor))
        if precio_nuevo > precio_viejo:
            pct = int(round((precio_nuevo - precio_viejo) / precio_nuevo * 100.0))
        else:
            pct = 0
        return precio_nuevo, pct

    def _calcular_pct(self, precio_viejo, precio_nuevo):
        if precio_nuevo > precio_viejo:
            return int(round((precio_nuevo - precio_viejo) / precio_nuevo * 100.0))
        return 0

    def _escribir_precio(self, codigo, precio_viejo, precio_nuevo):
        """Publica el precio actualizado para que el sistema legacy lo lea."""
        try:
            with open(RUTA_JSON_COPILOTO, "w", encoding="utf-8") as f:
                json.dump(
                    {"codigo": codigo, "precio_viejo": precio_viejo,
                     "precio_nuevo": precio_nuevo, "ts": time.time()},
                    f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _poll(self):
        """Sondeo periódico del JSON compartido (cada 500 ms)."""
        datos = leer_seleccion()
        if datos:
            ts = datos.get("ts")
            if ts is not None and ts != self._ultimo_ts:
                self._ultimo_ts = ts
                self._actualizar(datos)
        self.root.after(500, self._poll)

    def _refrescar(self):
        datos = leer_seleccion()
        if datos:
            self._ultimo_ts = datos.get("ts")
            self._actualizar(datos)

    def _actualizar(self, datos):
        evento = datos.get("evento", datos.get("estado"))

        if evento in ("limpiar", "sin_seleccion"):
            self._ocultar_notificacion()
            self._facturado = False
            self._precio_nuevo = None
            self._codigo_actual = None
            self._items = []
            self._actualizar_boton_enviar()
            self._mostrar_vacio()
            self.lbl_status.configure(text="Sincronizado · " + time.strftime("%H:%M:%S"))
            return

        if evento == "no_encontrado":
            self._ocultar_notificacion()
            self._facturado = False
            self._precio_nuevo = None
            self._codigo_actual = None
            self._items = []
            self._actualizar_boton_enviar()
            self.lbl_codigo.configure(text=datos.get("codigo", "—"))
            self.lbl_desc.configure(text="No encontrado en la tabla DBF")
            self.lbl_precio.configure(text="$ —")
            self.lbl_foxpro.configure(text="")
            self.lbl_medida.configure(text="")
            self.lbl_eq.configure(text="Sin equivalencia disponible")
            self.lbl_stock.configure(text="")
            self.lbl_status.configure(text="Sincronizado · " + time.strftime("%H:%M:%S"))
            return

        # --- Producto válido: seleccion / facturar / facturado ---
        precio_viejo = int(datos.get("precio", 0))
        codigo = datos.get("codigo", "")
        items = datos.get("items") or []

        if evento == "facturado":
            self._items = items
            if items:
                # Venta multi-producto: totaliza todos los ítems cargados
                subtotal, _iva, _total = self._totalizar_items(items)
                precio_nuevo = int(items[0].get("precio_unitario", precio_viejo))
                self._codigo_actual = items[0].get("codigo", codigo)
                self._descripcion_actual = items[0].get(
                    "descripcion", datos.get("descripcion", ""))
                self._cantidad_venta = sum(
                    int(it.get("cantidad", 0)) for it in items)
                self._total_venta = int(datos.get("total", round(subtotal)))
            else:
                # Compatibilidad: venta de un único ítem
                precio_nuevo = int(datos.get("precio_unitario", precio_viejo))
                self._codigo_actual = codigo
                self._descripcion_actual = datos.get("descripcion", "")
                self._cantidad_venta = int(datos.get("cantidad", 1))
                self._total_venta = int(datos.get("total", precio_nuevo))
            pct = self._calcular_pct(precio_viejo, precio_nuevo)
            self._facturado = True
        else:
            self._items = []
            precio_nuevo, pct = self._calcular_impacto(precio_viejo)
            self._codigo_actual = codigo
            self._descripcion_actual = datos.get("descripcion", "")
            self._cantidad_venta = int(datos.get("cantidad", 1))
            self._total_venta = int(datos.get("total", precio_nuevo))
            self._facturado = False

        self._precio_nuevo = precio_nuevo
        self._medida_actual = datos.get("medida", "")
        self._comprobante_actual = datos.get("comprobante", "")
        self._fecha_venta = datos.get("fecha", time.strftime("%d/%m/%Y"))
        self._hora_venta = datos.get("hora", time.strftime("%H:%M:%S"))

        self.lbl_codigo.configure(text=self._codigo_actual)
        self.lbl_desc.configure(text=self._descripcion_actual)
        self.lbl_precio.configure(text="$" + formatear_precio(precio_nuevo))
        self.lbl_foxpro.configure(
            text="En FoxPro: ${} (-{}% desactualizado)".format(
                formatear_precio(precio_viejo), pct))
        self.lbl_medida.configure(text=self._medida_actual)
        self.lbl_eq.configure(text=datos.get("equivalencia", "—"))
        self.lbl_stock.configure(
            text="Stock disponible: {} unidades".format(datos.get("stock", 0)))

        if evento == "facturar":
            self._escribir_precio(codigo, precio_viejo, precio_nuevo)
            self._notificar_inyeccion(precio_viejo, precio_nuevo)
        elif evento == "facturado":
            self._notificar_facturado(precio_nuevo)
        else:
            self._escribir_precio(codigo, precio_viejo, precio_nuevo)
            self._ocultar_notificacion()

        self._actualizar_boton_enviar()
        self.lbl_status.configure(text="Sincronizado · " + time.strftime("%H:%M:%S"))

    def _mostrar_vacio(self):
        self.lbl_codigo.configure(text="—")
        self.lbl_desc.configure(text="Esperando selección en sistema legacy...")
        self.lbl_precio.configure(text="$ —")
        self.lbl_foxpro.configure(text="")
        self.lbl_medida.configure(text="")
        self.lbl_eq.configure(text="—")
        self.lbl_stock.configure(text="")

    # ----------------------------------------------------- notificación
    def _notificar_inyeccion(self, precio_viejo, precio_nuevo):
        self.banner_notif.configure(fg_color=COLOR_NOTIF_BG, border_color=COLOR_NOTIF)
        self.lbl_notif.configure(
            text="» Inyectando Precio Actualizado (${} en vez de ${})".format(
                formatear_precio(precio_nuevo), formatear_precio(precio_viejo)))
        self._pulso_activo = 6
        self._pulso_notificacion()

    def _pulso_notificacion(self):
        if self._pulso_activo <= 0:
            self.lbl_notif.configure(text_color=COLOR_NOTIF)
            return
        self.lbl_notif.configure(
            text_color=COLOR_NOTIF if self._pulso_activo % 2 == 0 else COLOR_TEXTO)
        self._pulso_activo -= 1
        self.root.after(150, self._pulso_notificacion)

    def _ocultar_notificacion(self):
        self._pulso_activo = 0
        self.banner_notif.configure(fg_color=COLOR_FONDO, border_color=COLOR_FONDO)
        self.lbl_notif.configure(text=" ", text_color=COLOR_NOTIF)

    def _notificar_facturado(self, precio_nuevo):
        self.banner_notif.configure(fg_color=COLOR_OK_BG, border_color=COLOR_PRECIO)
        self.lbl_notif.configure(
            text="✔ Venta Facturada con Precio Actualizado (${})".format(
                formatear_precio(precio_nuevo)))
        self._pulso_activo = 6
        self._pulso_notificacion()

    def _actualizar_boton_enviar(self):
        if self._facturado and (self._codigo_actual or self._items):
            if len(self._items or []) > 1:
                texto = "Enviar Comprobante ({} ítems · ${})".format(
                    len(self._items), formatear_precio(self._total_venta))
            else:
                texto = "Enviar Comprobante por WhatsApp / Email (${})".format(
                    formatear_precio(self._total_venta))
            self.btn_enviar.configure(state="normal", text=texto)
        else:
            self.btn_enviar.configure(
                state="disabled",
                text="Enviar Comprobante por WhatsApp / Email")

    # ------------------------------------------------ generación de PDF
    def _totalizar_items(self, items):
        """Calcula Subtotal, IVA 21% y Total acumulado de una lista de ítems."""
        items = items or []
        subtotal = 0.0
        for it in items:
            try:
                cantidad = int(it.get("cantidad", 0))
            except (TypeError, ValueError):
                cantidad = 0
            try:
                precio = float(it.get("precio_unitario", 0))
            except (TypeError, ValueError):
                precio = 0.0
            subtotal += cantidad * precio
        iva = round(subtotal * IVA_PORCENTAJE / 100.0, 2)
        total = round(subtotal + iva, 2)
        return subtotal, iva, total

    def _generar_pdf(self):
        if not REPORTLAB_DISPONIBLE:
            raise RuntimeError("ReportLab no está instalado. Ejecute: pip install reportlab")

        ruta_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "factura_actualizada.pdf")
        codigo = self._codigo_actual or "—"
        detalle = self._descripcion_actual or ""
        if self._medida_actual:
            detalle = "{} · {}".format(detalle, self._medida_actual)
        cantidad = int(self._cantidad_venta or 1)
        precio_unitario = float(self._precio_nuevo or 0)
        items = self._items or []
        if items:
            subtotal, iva, total_final = self._totalizar_items(items)
        else:
            subtotal = precio_unitario * cantidad
            iva = round(subtotal * IVA_PORCENTAJE / 100.0, 2)
            total_final = round(subtotal + iva, 2)
        comprobante = self._comprobante_actual or "FAC-0001-00000000"
        fecha = self._fecha_venta or time.strftime("%d/%m/%Y")
        hora = self._hora_venta or time.strftime("%H:%M:%S")

        doc = SimpleDocTemplate(
            ruta_pdf, pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=16 * mm,
            title="Comprobante " + comprobante,
            author="JML Systems - Bulonera Rada Tilly")

        estilos = getSampleStyleSheet()
        titulo = ParagraphStyle("Titulo", parent=estilos["Title"], fontName="Helvetica-Bold",
                                fontSize=24, leading=26, textColor=colors.white)
        meta = ParagraphStyle("Meta", parent=estilos["Normal"], fontName="Helvetica-Bold",
                              fontSize=9, leading=12, textColor=colors.white, alignment=2)
        seccion = ParagraphStyle("Seccion", parent=estilos["Normal"], fontName="Helvetica-Bold",
                                 fontSize=10, leading=13, textColor=colors.HexColor("#0F172A"))
        cuerpo = ParagraphStyle("Cuerpo", parent=estilos["Normal"], fontName="Helvetica",
                                fontSize=9, leading=12, textColor=colors.HexColor("#334155"))
        pie = ParagraphStyle("Pie", parent=estilos["Normal"], fontName="Helvetica",
                             fontSize=7, leading=10, textColor=colors.HexColor("#94A3B8"))

        elementos = []

        cabecera = Table(
            [[Paragraph("JML SYSTEMS", titulo),
              Paragraph("COMPROBANTE DIGITAL<br/>" + comprobante, meta)]],
            colWidths=[80 * mm, 94 * mm])
        cabecera.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        elementos.append(cabecera)
        elementos.append(Spacer(1, 6 * mm))

        datos_emisor = Table(
            [[Paragraph("Bulonera Rada Tilly S.R.L. · Comodoro Rivadavia, Chubut", cuerpo),
              Paragraph("Fecha: {}<br/>Hora: {}".format(fecha, hora), cuerpo)]],
            colWidths=[80 * mm, 94 * mm])
        datos_emisor.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        elementos.append(datos_emisor)
        elementos.append(HRFlowable(width="100%", thickness=0.7,
                                    color=colors.HexColor("#CBD5E1"),
                                    spaceBefore=4, spaceAfter=8))

        elementos.append(Paragraph("CLIENTE", seccion))
        elementos.append(Paragraph(CLIENTE_DEMO + " · C.U.I.T. 30-00000000-0", cuerpo))
        elementos.append(Spacer(1, 6 * mm))

        elementos.append(Paragraph("DETALLE", seccion))
        elementos.append(Spacer(1, 2 * mm))
        # --- Tabla de detalle multi-producto (todas las filas cargadas) ---
        filas_detalle = [["Código", "Descripción", "Cant.", "Precio Unit.", "Subtotal"]]
        if items:
            for it in items:
                try:
                    cantidad_i = int(it.get("cantidad", 0))
                except (TypeError, ValueError):
                    cantidad_i = 0
                try:
                    precio_i = float(it.get("precio_unitario", 0))
                except (TypeError, ValueError):
                    precio_i = 0.0
                desc_i = it.get("descripcion", "")
                if it.get("medida"):
                    desc_i = "{} · {}".format(desc_i, it.get("medida"))
                filas_detalle.append([
                    it.get("codigo", ""),
                    Paragraph(desc_i, cuerpo),
                    str(cantidad_i),
                    formatear_monto(precio_i),
                    formatear_monto(precio_i * cantidad_i),
                ])
        else:
            filas_detalle.append([
                codigo, Paragraph(detalle, cuerpo), str(cantidad),
                formatear_monto(precio_unitario), formatear_monto(subtotal)])

        tabla_detalle = Table(filas_detalle,
                              colWidths=[26 * mm, 66 * mm, 16 * mm, 30 * mm, 30 * mm])
        tabla_detalle.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F8FAFC")])]))
        elementos.append(tabla_detalle)
        elementos.append(Spacer(1, 6 * mm))

        totales = Table(
            [["Subtotal (sin IVA)", formatear_monto(subtotal)],
             ["IVA ({:.0f}%)".format(IVA_PORCENTAJE), formatear_monto(iva)],
             ["TOTAL", formatear_monto(total_final)]],
            colWidths=[138 * mm, 30 * mm])
        totales.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.HexColor("#475569")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("FONTNAME", (0, -1), (1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (1, -1), 11),
            ("TEXTCOLOR", (0, -1), (1, -1), colors.HexColor("#0F172A")),
            ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#0F172A"))]))
        elementos.append(totales)

        elementos.append(Spacer(1, 10 * mm))
        elementos.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#E2E8F0"),
                                    spaceBefore=0, spaceAfter=4))
        elementos.append(Paragraph(
            "Documento generado automáticamente por Copiloto JML · " +
            time.strftime("%d/%m/%Y %H:%M:%S"), pie))

        doc.build(elementos)
        return ruta_pdf

    def _abrir_pdf(self, ruta_pdf):
        try:
            os.startfile(ruta_pdf)
        except Exception:
            try:
                webbrowser.open(ruta_pdf)
            except Exception:
                pass

    # ------------------------------------------------ envío digital
    def _simular_envio(self):
        if not self._facturado or (not self._codigo_actual and not self._items):
            self.lbl_status.configure(
                text="Facture una venta antes de enviar el comprobante")
            return

        # 1) Generar el PDF real de la factura
        try:
            ruta_pdf = self._generar_pdf()
        except Exception as exc:
            self.lbl_status.configure(text="No se pudo generar el PDF: " + str(exc))
            return

        # 2) Mostrar primero el popup de progreso (para que no quede tapado)
        comprobante = self._comprobante_actual or "FAC-0001-00000000"
        items = self._items or []
        if items:
            _subtotal, _iva, total_final_valor = self._totalizar_items(items)
            total_final = formatear_monto(total_final_valor)
            resumen = "{} · {} ítem(s) · TOTAL ${} (IVA incl.)".format(
                comprobante, len(items), total_final)
        else:
            total_final = formatear_monto(
                float(self._precio_nuevo or 0) * int(self._cantidad_venta or 1)
                * (1.0 + IVA_PORCENTAJE / 100.0))
            resumen = "{} · {} · {} u. × ${} = ${} (IVA incl.)".format(
                comprobante, self._codigo_actual, self._cantidad_venta,
                formatear_precio(self._precio_nuevo or 0), total_final)

        ventana = ctk.CTkToplevel(self.root)
        ventana.title("Envío de Comprobante")
        ventana.configure(fg_color=COLOR_FONDO)
        ventana.resizable(False, False)
        ventana.attributes("-topmost", True)
        ventana.lift()
        ventana.focus_force()

        w, h = 440, 300
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        ventana.geometry(f"{w}x{h}+{x}+{y}")

        ctk.CTkLabel(ventana, text="ENVÍO DE COMPROBANTE", font=(FUENTE, 15, "bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            ventana,
            text=resumen,
            font=(FUENTE, 12), text_color=COLOR_SECUNDARIO).pack(anchor="w", padx=20, pady=(2, 4))
        ctk.CTkLabel(
            ventana,
            text="Cliente: " + CLIENTE_DEMO,
            font=(FUENTE, 12), text_color=COLOR_SECUNDARIO).pack(anchor="w", padx=20, pady=(0, 12))

        self._prog = ctk.CTkProgressBar(ventana, width=400)
        self._prog.set(0)
        self._prog.pack(padx=20, pady=(0, 8))

        self._lbl_paso = ctk.CTkLabel(ventana, text="", font=(FUENTE, 12),
                                      text_color=COLOR_TEXTO)
        self._lbl_paso.pack(anchor="w", padx=20, pady=(0, 12))

        self._ventana_envio = ventana
        self._paso_idx = 0

        # 3) Abrir el PDF DESPUÉS de mostrar el popup
        self._abrir_pdf(ruta_pdf)

        # 4) Recuperar el frente justo después de disparar el visor de PDF
        ventana.after(200, lambda v=ventana: (
            v.attributes("-topmost", True), v.lift(), v.focus_force()))

        self._avanzar_paso()

    def _avanzar_paso(self):
        if self._paso_idx >= len(PASOS_ENVIO):
            self._ventana_envio.after(800, self._finalizar_envio)
            return
        texto, progreso = PASOS_ENVIO[self._paso_idx]
        self._lbl_paso.configure(text=texto)
        self._prog.set(progreso)
        self._paso_idx += 1
        self._ventana_envio.after(650, self._avanzar_paso)

    def _finalizar_envio(self):
        """Cierra el modal de progreso y muestra el aviso de éxito moderno."""
        try:
            self._ventana_envio.destroy()
        except Exception:
            pass
        self._mostrar_confirmacion_envio()

    def _mostrar_confirmacion_envio(self):
        """Aviso final con estética moderna del Copiloto (no messagebox clásico)."""
        comprobante = self._comprobante_actual or "FAC-0001-00000000"

        ventana = ctk.CTkToplevel(self.root)
        ventana.title("Confirmación de Envío")
        ventana.configure(fg_color=COLOR_FONDO)
        ventana.resizable(False, False)
        ventana.attributes("-topmost", True)
        ventana.transient(self.root)
        ventana.grab_set()
        ventana.lift()
        ventana.focus_force()

        w, h = 480, 280
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        ventana.geometry(f"{w}x{h}+{x}+{y}")

        # Tarjeta/diálogo moderno con borde verde de éxito
        tarjeta = ctk.CTkFrame(
            ventana, fg_color=COLOR_TARJETA, corner_radius=16,
            border_width=1, border_color=COLOR_PRECIO)
        tarjeta.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            tarjeta, text="✔", font=(FUENTE, 44, "bold"),
            text_color=COLOR_PRECIO).pack(anchor="w", padx=22, pady=(18, 0))
        ctk.CTkLabel(
            tarjeta,
            text="La factura {} fue enviada con éxito\nal WhatsApp del cliente.".format(
                comprobante),
            font=(FUENTE, 15, "bold"), text_color=COLOR_TEXTO,
            justify="left", anchor="w").pack(anchor="w", padx=22, pady=(8, 0))
        ctk.CTkLabel(
            tarjeta,
            text="Cliente: " + CLIENTE_DEMO,
            font=(FUENTE, 12), text_color=COLOR_SECUNDARIO,
            anchor="w").pack(anchor="w", padx=22, pady=(6, 0))

        ctk.CTkButton(
            tarjeta, text="Cerrar", width=130, height=36, corner_radius=10,
            fg_color=COLOR_ACENTO, hover_color="#0EA5E9",
            font=(FUENTE, 13, "bold"), text_color="#06222E",
            command=ventana.destroy).pack(anchor="e", padx=22, pady=(18, 0))

    def run(self):
        self.root.mainloop()


def main():
    if not CTK_DISPONIBLE:
        print("ERROR: 'customtkinter' no está instalado.")
        print("Instálalo con:  python -m pip install customtkinter")
        raise SystemExit(1)
    if not REPORTLAB_DISPONIBLE:
        print("ERROR: 'reportlab' no está instalado.")
        print("Instálalo con:  python -m pip install reportlab")
        raise SystemExit(1)
    CopilotoJML().run()


if __name__ == "__main__":
    main()
