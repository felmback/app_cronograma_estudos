import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import math
import json
import os


# Configurações
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
TEMPO_PADRAO = "1h Estudo"
PROGRESS_FILE = "progresso_estudos.json"
CONCURSO = "Polícia Rodoviaria Federal"

st.set_page_config(page_title=f"Cronograma de Estudos - {CONCURSO}", layout="wide")

# CSS para estilizar os cards e botões, incluindo o estado concluído (cinza claro)
st.markdown("""
<style>
.study-card {
    height: 150px;
    padding: 12px 16px 8px 16px;
    border-radius: 12px;
    box-shadow: 1px 3px 8px rgba(0, 0, 0, 0.12);
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.15s ease-in-out;
    color: #222;
}
.study-card:hover {
    transform: scale(1.04);
}
.study-card.concluido {
    background: #e0e0e0 !important;
    color: #777 !important;
    box-shadow: none !important;
}
.card-1 { background: linear-gradient(135deg, #d0f0d0, #f0fff0); }
.card-2 { background: linear-gradient(135deg, #d0e0f8, #f0f5ff); }
.card-3 { background: linear-gradient(135deg, #f8f8f8, #ffffff); }
.card-4 { background: linear-gradient(135deg, #e6e6e6, #f4f4f4); }
.card-5 { background: linear-gradient(135deg, #c0e6ff, #e6f6ff); }
.card-6 { background: linear-gradient(135deg, #d9f2e6, #f0fff5); }

.study-card p {
    margin: 4px 0;
    font-size: 14px;
    line-height: 1.2;
}

.week-title {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 16px;
    color: #111;
}

.checkbox-label {
    font-size: 13px;
    color: #444;
    margin-top: 8px;
    user-select: none;
}

.stDownloadButton > button {
    background-color: #005a9c;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
}
.stDownloadButton > button:hover {
    background-color: #0073cc;
}
</style>
""", unsafe_allow_html=True)

# --- Funções ---

def load_data(file, cols=None):
    try:
        df = pd.read_excel(file)
        if cols:
            df = df[cols]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return None

def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
    plano = []
    for disc, group in df.groupby(col_disciplina):
        for _, row in group.iterrows():
            assunto = row[col_assunto]
            carga = row[col_carga]
            carga_int = int(carga)
            carga_decimal = carga - carga_int

            for i in range(carga_int):
                plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

            if carga_decimal > 0:
                plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

            plano.append((disc, f"Revisão {assunto}", "Revisão"))

    return plano

def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
    plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
    data_atual = data_inicio
    linhas = []

    for disc, assunto, tipo in plano:
        while data_atual.weekday() == 6:  # pula domingos
            data_atual += timedelta(days=1)

        dia_semana = DIAS_SEMANA[data_atual.weekday()]

        linhas.append({
            "id": f"{disc}::{assunto}",
            "Data": data_atual.strftime("%d/%m/%Y"),
            "Dia da Semana": dia_semana,
            "Disciplina": disc,
            "Assunto": assunto,
            "Tipo": tipo,
            "Tempo": TEMPO_PADRAO
        })

        data_atual += timedelta(days=1)

    return pd.DataFrame(linhas)

def salvar_progresso(progresso):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progresso, f)

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    else:
        return {}

# Inicializa progresso no session_state
if "progresso" not in st.session_state:
    st.session_state["progresso"] = carregar_progresso()

st.title(f"Cronograma de Estudos - {CONCURSO}")

# Sidebar para upload e data de início
st.sidebar.header("Configurações")
data_inicio = st.sidebar.date_input("Data de Início", datetime(2025, 10, 20))
arquivo = st.sidebar.file_uploader("Upload do Edital Verticalizado (.xlsx)", type=["xlsx"])

if arquivo:
    col_disciplina = "Disciplina"
    col_assunto = "Assunto"
    col_carga = "Estudo (h)"

    df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

    if df_base is not None:
        cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

        # Atualiza coluna "Já Estudada"
        cronograma["Já Estudada"] = cronograma["id"].apply(
            lambda x: "Sim" if x in st.session_state["progresso"] else "Não"
        )

        total_itens = len(cronograma)
        estudados = len(st.session_state["progresso"])
        porcentagem = (estudados / total_itens * 100) if total_itens > 0 else 0

        st.markdown(f"### Progresso geral: {estudados} / {total_itens} itens estudados ({porcentagem:.1f}%)")
        st.progress(porcentagem / 100)

        if total_itens == 0:
            st.success("Parabéns! Você concluiu todos os estudos.")

        else:
            # Mostrar todos itens, mudando a cor dos concluídos
            total_dias = len(cronograma)
            total_semanas = math.ceil(total_dias / 6) if total_dias > 0 else 1

            semana_atual = st.slider(
                "Semana",
                min_value=1,
                max_value=total_semanas,
                value=1,
                step=1,
                help="Selecione a semana para visualizar"
            )

            inicio = (semana_atual - 1) * 6
            fim = inicio + 6
            semana_df = cronograma.iloc[inicio:fim]

            st.markdown(f"<div class='week-title'>Semana {semana_atual}</div>", unsafe_allow_html=True)

            cols = st.columns(6)

            def toggle_progress(id_key):
                progresso = st.session_state["progresso"]
                if id_key in progresso:
                    progresso.pop(id_key)
                else:
                    progresso[id_key] = True
                salvar_progresso(progresso)

            for i in range(6):
                with cols[i]:
                    if i < len(semana_df):
                        row = semana_df.iloc[i]
                        concluido = row["id"] in st.session_state["progresso"]

                        card_classes = f"study-card card-{i+1}"
                        if concluido:
                            card_classes += " concluido"

                        st.markdown(f"""
                            <div class="{card_classes}">
                                <p><strong>{row['Data']} ({row['Dia da Semana']})</strong></p>
                                <p>{row['Assunto']}</p>
                                <p style="font-size:14px; color:#555;">{row['Disciplina']}</p>
                                <p style="font-size:12px; color:#555;">{row['Tempo']}</p>
                            </div>
                        """, unsafe_allow_html=True)

                        checked = concluido

                        st.checkbox(
                            "Conteúdo Concluído",
                            value=checked,
                            key=row["id"],
                            on_change=toggle_progress,
                            args=(row["id"],)
                        )
                    else:
                        st.markdown(f"""
                            <div class="study-card card-{i+1}" style="background: #f9f9f9; box-shadow:none;">
                                <p style="color:#bbb; text-align:center; margin-top: 50%;">Sem dado</p>
                            </div>
                        """, unsafe_allow_html=True)

        # Botão para resetar progresso
        if st.sidebar.button("Resetar Progresso"):
            st.session_state["progresso"] = {}
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
            st.experimental_rerun()

        # Botão para download do cronograma atualizado
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
        output.seek(0)

        st.download_button(
            label="Baixar cronograma completo (Excel)",
            data=output,
            file_name="Cronograma_Estudos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Faça upload do arquivo Excel com o edital verticalizado.")

# import streamlit as st
# import pandas as pd
# from datetime import datetime, timedelta
# import io
# import math
# import json
# import os

# # Configurações
# DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# TEMPO_PADRAO = "1h Estudo"
# PROGRESS_FILE = "progresso_estudos.json"
# CONCURSO = "Polícia Rodoviaria Federal"

# st.set_page_config(page_title=f"Cronograma de Estudos - {CONCURSO}", layout="wide")

# # CSS para estilizar os cards e botões
# st.markdown("""
# <style>
# .study-card {
#     height: 150px;
#     padding: 12px 16px 8px 16px;
#     border-radius: 12px;
#     box-shadow: 1px 3px 8px rgba(0, 0, 0, 0.12);
#     margin-bottom: 16px;
#     display: flex;
#     flex-direction: column;
#     justify-content: space-between;
#     transition: transform 0.15s ease-in-out;
# }
# .study-card:hover {
#     transform: scale(1.04);
# }
# .card-1 { background: linear-gradient(135deg, #d0f0d0, #f0fff0); }
# .card-2 { background: linear-gradient(135deg, #d0e0f8, #f0f5ff); }
# .card-3 { background: linear-gradient(135deg, #f8f8f8, #ffffff); }
# .card-4 { background: linear-gradient(135deg, #e6e6e6, #f4f4f4); }
# .card-5 { background: linear-gradient(135deg, #c0e6ff, #e6f6ff); }
# .card-6 { background: linear-gradient(135deg, #d9f2e6, #f0fff5); }
# .study-card p {
#     margin: 4px 0;
#     font-size: 14px;
#     color: #222;
#     line-height: 1.2;
# }
# .week-title {
#     font-size: 24px;
#     font-weight: 700;
#     margin-bottom: 16px;
#     color: #111;
# }
# .checkbox-label {
#     font-size: 13px;
#     color: #444;
#     margin-top: 8px;
#     user-select: none;
# }
# .stDownloadButton > button {
#     background-color: #005a9c;
#     color: white;
#     padding: 10px 20px;
#     border: none;
#     border-radius: 5px;
# }
# .stDownloadButton > button:hover {
#     background-color: #0073cc;
# }
# </style>
# """, unsafe_allow_html=True)

# # --- Funções ---

# def load_data(file, cols=None):
#     try:
#         df = pd.read_excel(file)
#         if cols:
#             df = df[cols]
#         return df
#     except Exception as e:
#         st.error(f"Erro ao carregar o arquivo: {e}")
#         return None

# def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
#     plano = []
#     for disc, group in df.groupby(col_disciplina):
#         for _, row in group.iterrows():
#             assunto = row[col_assunto]
#             carga = row[col_carga]
#             carga_int = int(carga)
#             carga_decimal = carga - carga_int

#             for i in range(carga_int):
#                 plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

#             if carga_decimal > 0:
#                 plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

#             plano.append((disc, f"Revisão {assunto}", "Revisão"))

#     return plano

# def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
#     plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
#     data_atual = data_inicio
#     linhas = []

#     for disc, assunto, tipo in plano:
#         while data_atual.weekday() == 6:  # !=  domingo
#             data_atual += timedelta(days=1)

#         dia_semana = DIAS_SEMANA[data_atual.weekday()]

#         linhas.append({
#             "id": f"{disc}::{assunto}",
#             "Data": data_atual.strftime("%d/%m/%Y"),
#             "Dia da Semana": dia_semana,
#             "Disciplina": disc,
#             "Assunto": assunto,
#             "Tipo": tipo,
#             "Tempo": TEMPO_PADRAO
#         })

#         data_atual += timedelta(days=1)

#     return pd.DataFrame(linhas)

# def salvar_progresso(progresso):
#     with open(PROGRESS_FILE, "w") as f:
#         json.dump(progresso, f)

# def carregar_progresso():
#     if os.path.exists(PROGRESS_FILE):
#         try:
#             with open(PROGRESS_FILE, "r") as f:
#                 return json.load(f)
#         except:
#             return {}
#     else:
#         return {}

# # --- Inicialização do progresso no session_state ---
# if "progresso" not in st.session_state:
#     st.session_state["progresso"] = carregar_progresso()

# # --- Interface ---

# st.title(f"Cronograma de Estudos - {CONCURSO}")

# # Sidebar para upload e data de início
# st.sidebar.header("Configurações")
# data_inicio = st.sidebar.date_input("Data de Início", datetime(2025, 10, 20))
# arquivo = st.sidebar.file_uploader("Upload do Edital Verticalizado (.xlsx)", type=["xlsx"])

# if arquivo:
#     col_disciplina = "Disciplina"
#     col_assunto = "Assunto"
#     col_carga = "Estudo (h)"

#     df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

#     if df_base is not None:
#         cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

#         # Atualiza coluna "Já Estudada"
#         cronograma["Já Estudada"] = cronograma["id"].apply(
#             lambda x: "Sim" if x in st.session_state["progresso"] else "Não"
#         )

#         total_itens = len(cronograma)
#         estudados = len(st.session_state["progresso"])
#         porcentagem = (estudados / total_itens * 100) if total_itens > 0 else 0

#         st.markdown(f"### Progresso geral: {estudados} / {total_itens} itens estudados ({porcentagem:.1f}%)")
#         st.progress(porcentagem / 100)

#         if total_itens == 0:
#             st.success("Parabéns! Você concluiu todos os estudos.")

#         else:
#             # Mostrar só itens não estudados
#             nao_estudados = cronograma[cronograma["Já Estudada"] == "Não"]

#             total_dias = len(nao_estudados)
#             total_semanas = math.ceil(total_dias / 6) if total_dias > 0 else 1

#             semana_atual = st.slider(
#                 "Semana",
#                 min_value=1,
#                 max_value=total_semanas,
#                 value=1,
#                 step=1,
#                 help="Selecione a semana para visualizar"
#             )

#             inicio = (semana_atual - 1) * 6
#             fim = inicio + 6
#             semana_df = nao_estudados.iloc[inicio:fim]

#             st.markdown(f"<div class='week-title'>Semana {semana_atual}</div>", unsafe_allow_html=True)

#             cols = st.columns(6)

#             # Função para lidar com o toggle checkbox
#             def toggle_progress(id_key):
#                 progresso = st.session_state["progresso"]
#                 if id_key in progresso:
#                     progresso.pop(id_key)
#                 else:
#                     progresso[id_key] = True
#                 salvar_progresso(progresso)

#             for i in range(6):
#                 with cols[i]:
#                     if i < len(semana_df):
#                         row = semana_df.iloc[i]

#                         st.markdown(f"""
#                             <div class="study-card card-{i+1}">
#                                 <p><strong>{row['Data']} ({row['Dia da Semana']})</strong></p>
#                                 <p>{row['Assunto']}</p>
#                                 <p style="font-size:18x; color:#555;">{row['Disciplina']}</p>
#                                 <p style="font-size:12px; color:#555;">{row['Tempo']}</p>
#                         """, unsafe_allow_html=True)

#                         checked = row["id"] in st.session_state["progresso"]

#                         st.checkbox(
#                             "Conteúdo Concluído",
#                             value=checked,
#                             key=row["id"],
#                             on_change=toggle_progress,
#                             args=(row["id"],)
#                         )

#                         st.markdown("</div>", unsafe_allow_html=True)
#                     else:
#                         st.markdown(f"""
#                             <div class="study-card card-{i+1}" style="background: #f9f9f9; box-shadow:none;">
#                                 <p style="color:#bbb; text-align:center; margin-top: 50%;">Sem dado</p>
#                             </div>
#                         """, unsafe_allow_html=True)

#         # Botão para resetar progresso
#         if st.sidebar.button("Resetar Progresso"):
#             st.session_state["progresso"] = {}
#             if os.path.exists(PROGRESS_FILE):
#                 os.remove(PROGRESS_FILE)
#             st.experimental_rerun()

#         # Botão para download do cronograma atualizado
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
#         output.seek(0)

#         st.download_button(
#             label="Baixar cronograma completo (Excel)",
#             data=output,
#             file_name="Cronograma_Estudos.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )

# else:
#     st.info("Faça upload do arquivo Excel com o edital verticalizado.")

# import streamlit as st
# import pandas as pd
# from datetime import datetime, timedelta
# import io
# import math
# import json
# import os

# # Configurações
# DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# TEMPO_PADRAO = "1h Estudo"
# PROGRESS_FILE = "progresso_estudos.json"  # arquivo para salvar progresso

# st.set_page_config(page_title="Cronograma de Estudos", layout="wide")

# # CSS personalizado para cards
# st.markdown("""
#     <style>
#     .study-card {
#         height: 140px;
#         padding: 12px;
#         border-radius: 12px;
#         box-shadow: 1px 3px 8px rgba(0, 0, 0, 0.12);
#         margin-bottom: 16px;
#         display: flex;
#         flex-direction: column;
#         justify-content: center;
#         transition: transform 0.15s ease-in-out;
#     }

#     .study-card:hover {
#         transform: scale(1.04);
#     }

#     .card-1 { background: linear-gradient(135deg, #d0f0d0, #f0fff0); }
#     .card-2 { background: linear-gradient(135deg, #d0e0f8, #f0f5ff); }
#     .card-3 { background: linear-gradient(135deg, #f8f8f8, #ffffff); }
#     .card-4 { background: linear-gradient(135deg, #e6e6e6, #f4f4f4); }
#     .card-5 { background: linear-gradient(135deg, #c0e6ff, #e6f6ff); }
#     .card-6 { background: linear-gradient(135deg, #d9f2e6, #f0fff5); }

#     .study-card p {
#         margin: 4px 0;
#         font-size: 14px;
#         color: #222;
#         line-height: 1.2;
#     }

#     .week-title {
#         font-size: 24px;
#         font-weight: 700;
#         margin-bottom: 16px;
#         color: #111;
#     }

#     .stDownloadButton > button {
#         background-color: #005a9c;
#         color: white;
#         padding: 10px 20px;
#         border: none;
#         border-radius: 5px;
#     }

#     .stDownloadButton > button:hover {
#         background-color: #0073cc;
#     }

#     .checkbox-container {
#         margin-top: 8px;
#         font-size: 13px;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # Sidebar com inputs
# st.sidebar.header("Configurações")
# data_inicio = st.sidebar.date_input("Data de Início", datetime(2025, 10, 20))
# arquivo = st.sidebar.file_uploader("Upload do Edital Verticalizado (.xlsx)", type=["xlsx"])

# col_disciplina = "Disciplina"
# col_assunto = "Assunto"
# col_carga = "Estudo (h)"

# def load_data(file, cols=None):
#     try:
#         df = pd.read_excel(file)
#         if cols:
#             df = df[cols]
#         return df
#     except Exception as e:
#         st.error(f"Erro ao carregar o arquivo: {e}")
#         return None

# def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
#     plano = []
#     for disc, group in df.groupby(col_disciplina):
#         for _, row in group.iterrows():
#             assunto = row[col_assunto]
#             carga = row[col_carga]
#             carga_int = int(carga)
#             carga_decimal = carga - carga_int

#             for i in range(carga_int):
#                 plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

#             if carga_decimal > 0:
#                 plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

#             plano.append((disc, f"Revisão {assunto}", "Revisão"))

#     return plano

# def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
#     plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
#     data_atual = data_inicio
#     linhas = []

#     for disc, assunto, tipo in plano:
#         while data_atual.weekday() == 6:  # Pular domingos
#             data_atual += timedelta(days=1)

#         dia_semana = DIAS_SEMANA[data_atual.weekday()]

#         linhas.append({
#             "id": f"{disc}::{assunto}",  # id único para salvar status
#             "Data": data_atual.strftime("%d/%m/%Y"),
#             "Dia da Semana": dia_semana,
#             "Disciplina": disc,
#             "Assunto": assunto,
#             "Tipo": tipo,
#             "Tempo": TEMPO_PADRAO
#         })

#         data_atual += timedelta(days=1)

#     return pd.DataFrame(linhas)

# def load_progress():
#     if os.path.exists(PROGRESS_FILE):
#         with open(PROGRESS_FILE, "r") as f:
#             return json.load(f)
#     return {}

# def save_progress(progress_dict):
#     with open(PROGRESS_FILE, "w") as f:
#         json.dump(progress_dict, f)

# st.title("Cronograma de Estudos")

# if arquivo:
#     df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

#     if df_base is not None:
#         cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

#         # Carregar progresso salvo
#         progresso = load_progress()

#         # Filtrar só não estudados
#         cronograma = cronograma[~cronograma["id"].isin(progresso.keys())]

#         total_itens = len(cronograma) + len(progresso)
#         estudados = len(progresso)
#         porcentagem = (estudados / total_itens * 100) if total_itens > 0 else 0

#         st.markdown(f"### Progresso geral: {estudados} / {total_itens} itens estudados ({porcentagem:.1f}%)")
#         progresso_bar = st.progress(porcentagem / 100)

#         if total_itens == 0:
#             st.success("Parabéns! Você concluiu todos os estudos.")

#         else:
#             total_dias = len(cronograma)
#             total_semanas = math.ceil(total_dias / 6) if total_dias > 0 else 1

#             semana_atual = st.slider(
#                 "Semana",
#                 min_value=1,
#                 max_value=total_semanas,
#                 value=1,
#                 step=1,
#                 help="Selecione a semana para visualizar"
#             )

#             inicio = (semana_atual - 1) * 6
#             fim = inicio + 6
#             semana_df = cronograma.iloc[inicio:fim]

#             st.markdown(f"<div class='week-title'>Semana {semana_atual}</div>", unsafe_allow_html=True)

#             cols = st.columns(6)

#             # Função para atualizar o progresso ao marcar checkbox
#             def toggle_progress(id_key, checked):
#                 if checked:
#                     progresso[id_key] = True
#                 else:
#                     if id_key in progresso:
#                         progresso.pop(id_key)
#                 save_progress(progresso)

#             for i in range(6):
#                 with cols[i]:
#                     if i < len(semana_df):
#                         row = semana_df.iloc[i]
#                         # checkbox para marcar estudado
#                         checked = st.checkbox(
#                             label=f"{row['Data']} ({row['Dia da Semana']}) - {row['Assunto']}",
#                             key=row['id']
#                         )
#                         if checked:
#                             toggle_progress(row['id'], True)

#                         st.markdown(f"""
#                             <div class="study-card card-{i+1}">
#                                 <p><strong>{row['Data']} ({row['Dia da Semana']})</strong></p>
#                                 <p>{row['Assunto']}</p>
#                                 <p style="font-size:12px; color:#555;">{row['Disciplina']}</p>
#                                 <p style="font-size:12px; color:#555;">{row['Tempo']}</p>
#                             </div>
#                         """, unsafe_allow_html=True)
#                     else:
#                         st.markdown(f"""
#                             <div class="study-card card-{i+1}" style="background: #f9f9f9; box-shadow:none;">
#                                 <p style="color:#bbb; text-align:center; margin-top: 50%;">Sem dado</p>
#                             </div>
#                         """, unsafe_allow_html=True)

#         if st.sidebar.button("Resetar Progresso"):
#             if os.path.exists(PROGRESS_FILE):
#                 os.remove(PROGRESS_FILE)
#             st.experimental_rerun()

#         # Botão para baixar cronograma completo
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
#         output.seek(0)

#         st.download_button(
#             label="Baixar cronograma completo (Excel)",
#             data=output,
#             file_name="Cronograma_Estudos.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )

# else:
#     st.info("Faça upload do arquivo Excel com o edital verticalizado.")



# ## muito proximo do que eu quero, mas ainda n 100%
# import streamlit as st
# import pandas as pd
# from datetime import datetime, timedelta
# import io
# import math

# # Configurações
# DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# TEMPO_PADRAO = "1h Estudo"

# st.set_page_config(page_title="Cronograma de Estudos", layout="wide")

# # CSS personalizado para cards
# st.markdown("""
#     <style>
#     .study-card {
#         height: 140px;
#         padding: 12px;
#         border-radius: 12px;
#         box-shadow: 1px 3px 8px rgba(0, 0, 0, 0.12);
#         margin-bottom: 16px;
#         display: flex;
#         flex-direction: column;
#         justify-content: center;
#         transition: transform 0.15s ease-in-out;
#     }

#     .study-card:hover {
#         transform: scale(1.04);
#     }

#     /* Cores em degradê alternadas para os 6 cards */
#     .card-1 { background: linear-gradient(135deg, #d0f0d0, #f0fff0); }
#     .card-2 { background: linear-gradient(135deg, #d0e0f8, #f0f5ff); }
#     .card-3 { background: linear-gradient(135deg, #f8f8f8, #ffffff); }
#     .card-4 { background: linear-gradient(135deg, #e6e6e6, #f4f4f4); }
#     .card-5 { background: linear-gradient(135deg, #c0e6ff, #e6f6ff); }
#     .card-6 { background: linear-gradient(135deg, #d9f2e6, #f0fff5); }

#     .study-card p {
#         margin: 4px 0;
#         font-size: 14px;
#         color: #222;
#         line-height: 1.2;
#     }

#     .week-title {
#         font-size: 24px;
#         font-weight: 700;
#         margin-bottom: 16px;
#         color: #111;
#     }

#     .stDownloadButton > button {
#         background-color: #005a9c;
#         color: white;
#         padding: 10px 20px;
#         border: none;
#         border-radius: 5px;
#     }

#     .stDownloadButton > button:hover {
#         background-color: #0073cc;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # Sidebar com inputs
# st.sidebar.header("Configurações")
# data_inicio = st.sidebar.date_input("Data de Início", datetime(2025, 10, 20))
# arquivo = st.sidebar.file_uploader("Upload do Edital Verticalizado (.xlsx)", type=["xlsx"])

# # Colunas fixas
# col_disciplina = "Disciplina"
# col_assunto = "Assunto"
# col_carga = "Estudo (h)"

# def load_data(file, cols=None):
#     try:
#         df = pd.read_excel(file)
#         if cols:
#             df = df[cols]
#         return df
#     except Exception as e:
#         st.error(f"Erro ao carregar o arquivo: {e}")
#         return None

# def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
#     plano = []
#     for disc, group in df.groupby(col_disciplina):
#         for _, row in group.iterrows():
#             assunto = row[col_assunto]
#             carga = row[col_carga]
#             carga_int = int(carga)
#             carga_decimal = carga - carga_int

#             for i in range(carga_int):
#                 plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

#             if carga_decimal > 0:
#                 plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

#             plano.append((disc, f"Revisão {assunto}", "Revisão"))

#     return plano

# def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
#     plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
#     data_atual = data_inicio
#     linhas = []

#     for disc, assunto, tipo in plano:
#         while data_atual.weekday() == 6:  # Pular domingos
#             data_atual += timedelta(days=1)

#         dia_semana = DIAS_SEMANA[data_atual.weekday()]

#         linhas.append({
#             "Data": data_atual.strftime("%d/%m/%Y"),
#             "Dia da Semana": dia_semana,
#             "Disciplina": disc,
#             "Assunto": assunto,
#             "Tipo": tipo,
#             "Tempo": TEMPO_PADRAO
#         })

#         data_atual += timedelta(days=1)

#     return pd.DataFrame(linhas)

# st.title("Cronograma de Estudos")

# if arquivo:
#     df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

#     if df_base is not None:
#         cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

#         total_dias = len(cronograma)
#         total_semanas = math.ceil(total_dias / 6)

#         # Controle da semana atual via slider
#         semana_atual = st.slider(
#             "Semana",
#             min_value=1,
#             max_value=total_semanas,
#             value=1,
#             step=1,
#             help="Selecione a semana para visualizar"
#         )

#         # Extrair dados da semana atual
#         inicio = (semana_atual - 1) * 6
#         fim = inicio + 6
#         semana_df = cronograma.iloc[inicio:fim]

#         st.markdown(f"<div class='week-title'>Semana {semana_atual}</div>", unsafe_allow_html=True)

#         # Criar 6 colunas - um card por coluna (seg a sáb)
#         cols = st.columns(6)

#         # Preencher cards (se faltar dados, exibir vazio)
#         for i in range(6):
#             with cols[i]:
#                 if i < len(semana_df):
#                     row = semana_df.iloc[i]
#                     # Card com classe para cor (degradê alternado)
#                     st.markdown(f"""
#                         <div class="study-card card-{i+1}">
#                             <p><strong>{row['Data']} ({row['Dia da Semana']})</strong></p>
#                             <p>{row['Assunto']}</p>
#                             <p style="font-size:12px; color:#555;">{row['Disciplina']}</p>
#                             <p style="font-size:12px; color:#555;">{row['Tempo']}</p>
#                         </div>
#                     """, unsafe_allow_html=True)
#                 else:
#                     # Coluna vazia para completar 6 colunas sempre
#                     st.markdown(f"""
#                         <div class="study-card card-{i+1}" style="background: #f9f9f9; box-shadow:none;">
#                             <p style="color:#bbb; text-align:center; margin-top: 50%;">Sem dado</p>
#                         </div>
#                     """, unsafe_allow_html=True)

#         # Botão para baixar o cronograma completo em Excel
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
#         output.seek(0)

#         st.download_button(
#             label="Baixar cronograma completo (Excel)",
#             data=output,
#             file_name="Cronograma_Estudos.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )

#         st.info(f"Início: {cronograma.iloc[0]['Data']} | Fim: {cronograma.iloc[-1]['Data']} | Total de dias: {len(cronograma)}")

# else:
#     st.info("Faça upload do arquivo Excel com o edital verticalizado.")



# import streamlit as st
# import pandas as pd
# from datetime import datetime, timedelta
# import io

# # === Configurações ===
# DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# TEMPO_PADRAO = "1h Estudo"

# # === Layout da Página ===
# st.set_page_config(page_title="📚 Cronograma de Estudos", layout="wide")

# # === Estilo CSS personalizado ===
# st.markdown("""
#     <style>
#     /* Fundo geral */
#     .stApp {
#         background-color: #f0f4f8;
#         color: #000000;
#         font-family: 'Segoe UI', sans-serif;
#     }

#     /* Título principal */
#     h1 {
#         color: #003366;
#         margin-bottom: 30px;
#     }

#     /* Cards */
#     .card {
#         border-radius: 10px;
#         padding: 20px;
#         margin-bottom: 15px;
#         box-shadow: 1px 1px 8px rgba(0,0,0,0.1);
#     }

#     .estudo {
#         background-color: #e6f2ff;
#         border-left: 6px solid #3399ff;
#     }

#     .revisao {
#         background-color: #f2f2f2;
#         border-left: 6px solid #666666;
#     }

#     .card h4 {
#         color: #001f3f;
#         margin-bottom: 10px;
#     }

#     .card p {
#         margin: 5px 0;
#         font-size: 16px;
#     }

#     /* Botão de download */
#     .stDownloadButton>button {
#         background-color: #004080;
#         color: white;
#         border-radius: 5px;
#         padding: 10px 20px;
#     }

#     .stDownloadButton>button:hover {
#         background-color: #0059b3;
#         color: #ffffff;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # === Título ===
# st.title("📚 Gerador de Cronograma de Estudos")

# # === Sidebar ===
# st.sidebar.header("📂 Parâmetros de Entrada")
# data_inicio = st.sidebar.date_input("📅 Data de Início", datetime(2025, 10, 20))
# arquivo = st.sidebar.file_uploader("Enviar edital verticalizado (.xlsx)", type=["xlsx"])

# # === Constantes de coluna ===
# col_disciplina = "Disciplina"
# col_assunto = "Assunto"
# col_carga = "Estudo (h)"

# # === Funções ===
# def load_data(file, cols=None):
#     try:
#         df = pd.read_excel(file)
#         if cols:
#             df = df[cols]
#         return df
#     except Exception as e:
#         st.error(f"Erro ao carregar o arquivo: {e}")
#         return None

# def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
#     plano = []
#     for disc, group in df.groupby(col_disciplina):
#         for _, row in group.iterrows():
#             assunto = row[col_assunto]
#             carga = row[col_carga]
#             carga_int = int(carga)
#             carga_decimal = carga - carga_int

#             for i in range(carga_int):
#                 plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

#             if carga_decimal > 0:
#                 plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

#             plano.append((disc, f"Revisão {assunto}", "Revisão"))

#     return plano

# def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
#     plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
#     data_atual = data_inicio
#     linhas = []

#     for disc, assunto, tipo in plano:
#         while data_atual.weekday() == 6:
#             data_atual += timedelta(days=1)

#         dia_semana = DIAS_SEMANA[data_atual.weekday()]

#         observacao = (
#             f"{tipo}: {assunto} - Leitura + Resumo + Questões"
#             if tipo == "Estudo"
#             else f"{tipo}: {assunto} - Revisão + 10 questões PRF"
#         )

#         linhas.append({
#             "Data": data_atual.strftime("%d/%m/%Y"),
#             "Dia da Semana": dia_semana,
#             "Disciplina": disc,
#             "Assunto": assunto,
#             "Tipo": tipo,
#             "Tempo": TEMPO_PADRAO,
#             "Observação": observacao
#         })

#         data_atual += timedelta(days=1)

#     return pd.DataFrame(linhas)

# # === Execução principal ===
# if arquivo:
#     df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

#     if df_base is not None:
#         cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

#         st.subheader("📆 Cronograma Gerado")

#         # === Exibir como cards ===
#         for index, row in cronograma.iterrows():
#             tipo_classe = "estudo" if row["Tipo"] == "Estudo" else "revisao"
#             st.markdown(f"""
#                 <div class="card {tipo_classe}">
#                     <h4>📅 {row['Data']} ({row['Dia da Semana']})</h4>
#                     <p><strong>📘 Assunto:</strong> {row['Assunto']}</p>
#                     <p><strong>📚 Disciplina:</strong> {row['Disciplina']}</p>
#                     <p><strong>🔄 Tipo:</strong> {row['Tipo']}</p>
#                     <p><strong>⏰ Carga Horária:</strong> {row['Tempo']}</p>
#                 </div>
#             """, unsafe_allow_html=True)

#         # === Exportar para Excel ===
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
#         output.seek(0)

#         st.download_button(
#             label="📥 Baixar Cronograma em Excel",
#             data=output,
#             file_name="Cronograma_Estudos.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )

#         st.success(f"✅ Total de dias: {len(cronograma)}")
#         st.info(f"📅 Início: {cronograma.iloc[0]['Data']}  |  Fim: {cronograma.iloc[-1]['Data']}")
# else:
#     st.info("📝 Faça o upload do edital verticalizado na barra lateral para começar.")




# # import streamlit as st
# # import pandas as pd
# # from datetime import datetime, timedelta
# # import io

# # # === Configurações fixas ===
# # DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# # TEMPO_PADRAO = "1h Estudo"

# # # === Página ===
# # st.set_page_config(page_title="Gerador de Cronograma", layout="wide")
# # st.title("📚 Gerador de Cronograma de Estudos")

# # # === Sidebar ===
# # st.sidebar.header("📂 Carregar Arquivo")
# # data_inicio = st.sidebar.date_input("📅 Data de Início", datetime(2025, 10, 20))
# # arquivo = st.sidebar.file_uploader("Enviar edital verticalizado (.xlsx)", type=["xlsx"])

# # col_disciplina = "Disciplina"
# # col_assunto = "Assunto"
# # col_carga = "Estudo (h)"

# # # === Funções ===
# # def load_data(file, cols=None):
# #     try:
# #         df = pd.read_excel(file)
# #         if cols:
# #             df = df[cols]
# #         return df
# #     except Exception as e:
# #         st.error(f"Erro ao carregar o arquivo: {e}")
# #         return None

# # def expandir_assuntos(df, col_disciplina, col_assunto, col_carga):
# #     plano = []
# #     for disc, group in df.groupby(col_disciplina):
# #         for _, row in group.iterrows():
# #             assunto = row[col_assunto]
# #             carga = row[col_carga]
# #             carga_int = int(carga)
# #             carga_decimal = carga - carga_int

# #             for i in range(carga_int):
# #                 plano.append((disc, f"{assunto} - Parte {i+1}", "Estudo"))

# #             if carga_decimal > 0:
# #                 plano.append((disc, f"{assunto} - Parte final ({carga_decimal:.1f}h)", "Estudo"))

# #             plano.append((disc, f"Revisão {assunto}", "Revisão"))

# #     return plano

# # def gerar_cronograma(df, col_disciplina, col_assunto, col_carga, data_inicio):
# #     plano = expandir_assuntos(df, col_disciplina, col_assunto, col_carga)
# #     data_atual = data_inicio
# #     linhas = []

# #     for disc, assunto, tipo in plano:
# #         while data_atual.weekday() == 6:
# #             data_atual += timedelta(days=1)

# #         dia_semana = DIAS_SEMANA[data_atual.weekday()]

# #         observacao = (
# #             f"{tipo}: {assunto} - Leitura + Resumo + Questões"
# #             if tipo == "Estudo"
# #             else f"{tipo}: {assunto} - Revisão + 10 questões PRF"
# #         )

# #         linhas.append({
# #             "Data": data_atual.strftime("%d/%m/%Y"),
# #             "Dia da Semana": dia_semana,
# #             "Disciplina": disc,
# #             "Assunto": assunto,
# #             "Tipo": tipo,
# #             "Tempo": TEMPO_PADRAO,
# #             "Observação": observacao
# #         })

# #         data_atual += timedelta(days=1)

# #     return pd.DataFrame(linhas)

# # # === Execução ===
# # if arquivo:
# #     df_base = load_data(arquivo, cols=[col_disciplina, col_assunto, col_carga])

# #     if df_base is not None:
# #         cronograma = gerar_cronograma(df_base, col_disciplina, col_assunto, col_carga, data_inicio)

# #         st.subheader("📆 Visualização do Cronograma")

# #         # Mostrar cards estilizados
# #         for index, row in cronograma.iterrows():
# #             with st.container():
# #                 st.markdown(f"""
# #                     <div style="border:1px solid #ddd; border-radius:10px; padding:15px; margin-bottom:10px; background-color:#f9f9f9">
# #                         <h4 style="margin-bottom:5px;">📅 {row['Data']} ({row['Dia da Semana']})</h4>
# #                         <p style="margin:5px 0;"><strong>📘 Assunto:</strong> {row['Assunto']}</p>
# #                         <p style="margin:5px 0;"><strong>📚 Disciplina:</strong> {row['Disciplina']}</p>
# #                         <p style="margin:5px 0;"><strong>🔄 Tipo:</strong> {row['Tipo']}</p>
# #                         <p style="margin:5px 0;"><strong>⏰ Carga Horária:</strong> {row['Tempo']}</p>
# #                     </div>
# #                 """, unsafe_allow_html=True)

# #         # Exportar Excel
# #         output = io.BytesIO()
# #         with pd.ExcelWriter(output, engine='openpyxl') as writer:
# #             cronograma.to_excel(writer, index=False, sheet_name='Cronograma')
# #         output.seek(0)

# #         st.download_button(
# #             label="📥 Baixar Cronograma em Excel",
# #             data=output,
# #             file_name="Cronograma_Estudos.xlsx",
# #             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# #         )

# #         st.success(f"✅ Total de dias: {len(cronograma)}")
# #         st.info(f"📅 Início: {cronograma.iloc[0]['Data']}  |  Fim: {cronograma.iloc[-1]['Data']}")
# # else:
# #     st.info("📝 Faça o upload do edital verticalizado na barra lateral para começar.")
