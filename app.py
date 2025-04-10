import streamlit as st
from fpdf import FPDF
import pandas as pd
import smtplib
from email.message import EmailMessage
import os
import qrcode

# --- Funções Pix ---
def format_field(id, value):
    size = f"{len(value):02d}"
    return f"{id}{size}{value}"

def gerar_payload_pix(chave, nome, cidade, valor, txid="***"):
    valor_str = f"{valor:.2f}"

    payload = (
        "000201" +
        format_field("26", format_field("00", "br.gov.bcb.pix") + format_field("01", chave)) +
        "52040000" +
        "5303986" +
        format_field("54", valor_str) +
        "5802BR" +
        format_field("59", nome) +
        format_field("60", cidade) +
        format_field("62", format_field("05", format_field("01", txid))) +
        "6304"  # CRC será inserido após cálculo
    )

    crc = calcular_crc16(payload)
    return payload + crc

def calcular_crc16(payload):
    """Calcula o CRC-16 CCITT-FALSE"""
    polinomio = 0x1021
    resultado = 0xFFFF

    for char in payload:
        resultado ^= ord(char) << 8
        for _ in range(8):
            if resultado & 0x8000:
                resultado = (resultado << 1) ^ polinomio
            else:
                resultado <<= 1
            resultado &= 0xFFFF

    return f"{resultado:04X}"


# --- Interface do app ---
st.set_page_config(page_title="App de Cobrança", layout="centered")
st.title("📬 Gerador de Cobrança com Envio por E-mail")

with st.form("formulario"):
    nome = st.text_input("Nome do cliente")
    valor = st.text_input("Valor a pagar (R$)")
    vencimento = st.date_input("Data de vencimento")
    email = st.text_input("E-mail do cliente")
    descricao = st.text_area("Descrição (opcional)")

    enviar = st.form_submit_button("Gerar e Enviar Cobrança")

if enviar:
    if nome and valor and email:
        try:
            valor_float = float(valor.replace(",", "."))

            chave_pix = "11969000038"
            cidade = "Sao Paulo"
            payload = gerar_payload_pix(chave_pix, "Renée", cidade, valor_float)

            qr_img = qrcode.make(payload)
            qr_path = "qrcode_pix.png"
            qr_img.save(qr_path)

            # Criar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)

            if os.path.exists("logo.png"):
                pdf.image("logo.png", x=10, y=8, w=33)
                pdf.ln(25)
            else:
                pdf.ln(10)

            pdf.set_fill_color(230, 230, 230)
            pdf.cell(0, 10, "COBRANÇA", ln=True, align="C", fill=True)
            pdf.ln(10)

            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Cliente: {nome}", ln=True)
            pdf.cell(0, 10, f"Valor a pagar: R$ {valor}", ln=True)
            pdf.cell(0, 10, f"Vencimento: {vencimento}", ln=True)

            if descricao:
                pdf.multi_cell(0, 10, f"Descrição: {descricao}")
                pdf.ln(5)

            pdf.image(qr_path, x=60, w=90)
            pdf.ln(10)

            pdf.set_font("Arial", "I", 10)
            pdf.multi_cell(0, 10, "Favor realizar o pagamento até a data de vencimento para evitar juros e encargos.")
            pdf.ln(5)
            pdf.cell(0, 10, "Atenciosamente,", ln=True)
            pdf.cell(0, 10, "Departamento Financeiro", ln=True)

            pdf.output("cobranca.pdf")

            # Enviar e-mail
            email_remetente = "reneedacomet@gmail.com"
            senha = "ywqy mhwv mtac hkyr"

            msg = EmailMessage()
            msg["Subject"] = "Cobrança"
            msg["From"] = email_remetente
            msg["To"] = email
            msg.set_content(f"Olá {nome}, segue em anexo sua cobrança no valor de R$ {valor} com vencimento em {vencimento}.")

            with open("cobranca.pdf", "rb") as arq:
                msg.add_attachment(arq.read(), maintype="application", subtype="pdf", filename="cobranca.pdf")

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(email_remetente, senha)
                smtp.send_message(msg)

            st.success("Cobrança enviada por e-mail com sucesso!")

            # Histórico
            novo = pd.DataFrame([{
                "Cliente": nome,
                "Valor": valor,
                "Vencimento": vencimento,
                "Email": email,
                "Descrição": descricao
            }])
            if os.path.exists("historico.csv"):
                historico = pd.read_csv("historico.csv")
                historico = pd.concat([historico, novo], ignore_index=True)
            else:
                historico = novo
            historico.to_csv("historico.csv", index=False)

        except Exception as e:
            st.error(f"Erro ao processar a cobrança: {e}")
    else:
        st.error("Preencha todos os campos!")
