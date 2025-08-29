import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
from datetime import datetime, date

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# --- Credenciales desde Streamlit Secrets ---
creds_dict = st.secrets["google_service_account"]
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)

CLIENT = gspread.authorize(CREDS)


SHEET_NAME = "Tareas"  # 📌 nombre de tu hoja
try:
    sheet = CLIENT.open(SHEET_NAME).sheet1
except Exception:
    st.error(f"No pude abrir la hoja '{SHEET_NAME}'. Verifica que existe y que compartiste acceso con el Service Account.")
    st.stop()

# --- 🌸 Estilo general ---
st.set_page_config(page_title="Agenda Rosita 🌸", page_icon="🌸", layout="wide")

# --- 📌 Categorías unificadas ---
CATEGORIAS = [
    "Estudio", "Trabajo", "Salud", "Hogar", "Finanzas", 
    "Amigos", "Familia", "Ocio", "Mañana", "Tarde", "Noche", "Otro"
]

# --- 📌 Menú principal ---
menu = st.sidebar.radio("📒 Menú", ["📅 Agenda", "🔁 Rutinas", "📊 Estadísticas"])

# --- Funciones auxiliares ---
def cargar_tareas():
    """Descargar todas las tareas en un DataFrame"""
    tareas = sheet.get_all_records()
    if not tareas:
        return pd.DataFrame(columns=["Fecha", "Hora", "Tarea", "Categoria", "Completada"])
    df = pd.DataFrame(tareas)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Completada"] = df["Completada"].astype(str).str.lower().isin(["true", "1", "yes", "sí", "si"])
    return df

def agregar_tarea(fecha, hora, tarea, categoria):
    sheet.append_row([str(fecha), str(hora), tarea, categoria, "False"])

def actualizar_tarea(idx, completada):
    # Las filas en gspread comienzan en 1, +2 por encabezado
    sheet.update_cell(idx + 2, 5, str(completada))

def borrar_tarea(idx):
    sheet.delete_rows(idx + 2)

# --- 📅 Agenda ---
if menu == "📅 Agenda":
    st.header("📅 Mi Agenda Diaria")

    with st.form("nueva_tarea"):
        fecha = st.date_input("📆 Fecha", value=date.today())
        hora = st.time_input("⏰ Hora")
        tarea = st.text_input("📝 Descripción de la tarea")
        categoria = st.selectbox("🏷️ Categoría", CATEGORIAS)
        submit = st.form_submit_button("➕ Agregar Tarea")

        if submit and tarea:
            agregar_tarea(fecha, hora, tarea, categoria)
            st.success("✅ Tarea añadida")
            st.rerun()

    df = cargar_tareas()
    if df.empty:
        st.info("No tienes tareas aún.")
    else:
        fecha_sel = st.date_input("📌 Ver tareas de:", value=date.today())
        tareas_dia = df[df["Fecha"].dt.date == fecha_sel]

        for idx, row in tareas_dia.iterrows():
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.checkbox(f"{row['Hora']} - {row['Tarea']} ({row['Categoria']})",
                            value=row["Completada"], key=f"chk_{idx}",
                            on_change=actualizar_tarea, args=(idx, not row["Completada"]))
            with col2:
                if st.button("❌ Borrar", key=f"del_{idx}"):
                    borrar_tarea(idx)
                    st.rerun()

# --- 🔁 Rutinas ---
elif menu == "🔁 Rutinas":
    st.header("🔁 Rutinas Diarias")

    df = cargar_tareas()

    with st.form("nueva_rutina"):
        tarea = st.text_input("✨ Nueva rutina")
        categoria = st.selectbox("🏷️ Categoría", CATEGORIAS)
        submit = st.form_submit_button("➕ Agregar Rutina")

        if submit and tarea:
            agregar_tarea(date.today(), "Rutina", tarea, categoria)
            st.success("✅ Rutina añadida")
            st.rerun()

    rutinas = df[df["Hora"] == "Rutina"]
    if rutinas.empty:
        st.info("No tienes rutinas registradas.")
    else:
        for idx, row in rutinas.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.checkbox(f"{row['Tarea']} ({row['Categoria']})",
                            value=row["Completada"], key=f"rut_{idx}",
                            on_change=actualizar_tarea, args=(idx, not row["Completada"]))
            with col2:
                if st.button("❌ Borrar", key=f"del_rut_{idx}"):
                    borrar_tarea(idx)
                    st.rerun()

# --- 📊 Estadísticas ---
elif menu == "📊 Estadísticas":
    st.header("📊 Estadísticas de Progreso")

    df = cargar_tareas()

    if df.empty:
        st.info("Todavía no hay datos para mostrar 📂")
    else:
        # --- Submenú ---
        stats_menu = st.sidebar.radio("📊 Tipo de estadística", 
                                      ["📅 Diario", "📆 Semanal", "🗓️ Mensual", "🌟 Hábitos"])

        # --- 📅 Diario ---
        if stats_menu == "📅 Diario":
            hoy = datetime.now().date()
            df_hoy = df[df["Fecha"].dt.date == hoy]
            completadas_hoy = df_hoy["Completada"].sum()
            total_hoy = len(df_hoy)

            st.subheader("📅 Progreso Diario")
            st.metric("Tareas completadas hoy", f"{completadas_hoy}/{total_hoy}")

            if total_hoy == 0:
                st.info("No tienes tareas registradas hoy.")

        # --- 📆 Semanal ---
        elif stats_menu == "📆 Semanal":
            st.subheader("📆 Progreso Semanal")
            df["DiaSemana"] = df["Fecha"].dt.day_name(locale="es_ES")

            semanal = df.groupby("DiaSemana")["Completada"].mean().reset_index()
            if semanal.empty:
                st.info("Todavía no hay datos semanales.")
            else:
                fig1 = px.bar(semanal, x="DiaSemana", y="Completada",
                              title="Porcentaje de tareas completadas por día",
                              text=semanal["Completada"].apply(lambda x: f"{x:.0%}"),
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                fig1.update_traces(textposition="outside")
                st.plotly_chart(fig1)

        # --- 🗓️ Mensual ---
        elif stats_menu == "🗓️ Mensual":
            st.subheader("📅 Progreso Mensual")
            df["SemanaMes"] = df["Fecha"].dt.isocalendar().week

            mensual = df.groupby("SemanaMes")["Completada"].mean().reset_index()
            if mensual.empty:
                st.info("Todavía no hay datos mensuales.")
            else:
                fig2 = px.line(mensual, x="SemanaMes", y="Completada",
                               title="Progreso mensual (por semanas)",
                               markers=True,
                               color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig2)

        # --- 🌟 Hábitos ---
        elif stats_menu == "🌟 Hábitos":
            st.subheader("🌟 Hábitos más cumplidos")
            if "Categoria" in df.columns:
                habitos = df.groupby("Categoria")["Completada"].mean().reset_index()
                if habitos.empty:
                    st.info("No hay hábitos registrados aún.")
                else:
                    fig3 = px.bar(habitos, x="Categoria", y="Completada",
                                  title="Cumplimiento de hábitos por categoría",
                                  text=habitos["Completada"].apply(lambda x: f"{x:.0%}"),
                                  color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig3.update_traces(textposition="outside")
                    st.plotly_chart(fig3)
            else:
                st.warning("⚠️ No se encontró la columna 'Categoria' en la hoja.")

# --- 🔔 Notificaciones dentro de la app ---
def mostrar_notificaciones(df):
    ahora = datetime.now()
    proximas = df[
        (df["Fecha"].dt.date == ahora.date()) &  # Solo hoy
        (df["Hora"] != "Rutina") &               # Ignorar rutinas
        (pd.to_datetime(df["Hora"], errors="coerce").notna())  # Horas válidas
    ].copy()

    if not proximas.empty:
        proximas["Hora_dt"] = pd.to_datetime(proximas["Hora"], errors="coerce").dt.time
        for _, row in proximas.iterrows():
            hora_tarea = datetime.combine(ahora.date(), row["Hora_dt"])
            diff = (hora_tarea - ahora).total_seconds() / 60  # minutos

            if 0 <= diff <= 15 and not row["Completada"]:  
                st.warning(f"⏰ **¡Recuerda tu tarea!** {row['Tarea']} "
                           f"({row['Categoria']}) a las {row['Hora']}")

                # --- 🔊 Sonido de alerta ---
                st.markdown(
                    """
                    <audio autoplay>
                      <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
                    </audio>
                    """,
                    unsafe_allow_html=True
                )


