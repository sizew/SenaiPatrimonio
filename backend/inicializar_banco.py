"""Reinicia o banco e mantém somente a conta da Secretaria e a sala de informática.

Este comando apaga usuários, crachás, patrimônios e históricos existentes.
Execute apenas quando quiser começar uma instalação limpa.
"""
import os
import sqlite3

from app import DB_FILE, init_db
from werkzeug.security import generate_password_hash


LABORATORIOS_PADRAO = [
    ("Sala de Informática", "Sala de Informática"),
]


def inicializar_banco():
    init_db()
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for tabela in ("cautelas", "leituras_rfid", "crachas_recentes", "patrimonios", "laboratorios", "usuarios"):
        cursor.execute(f"DELETE FROM {tabela}")
    cursor.execute("DELETE FROM sqlite_sequence")

    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        ("Secretaria SENAI", "secretaria@senai.br", generate_password_hash("senai123"), "secretaria"),
    )
    cursor.executemany(
        "INSERT INTO laboratorios (nome, localizacao, status) VALUES (?, ?, 'Livre')",
        LABORATORIOS_PADRAO,
    )

    conn.commit()
    conn.close()
    print("Banco reiniciado.")
    print("Conta: Secretaria | Professores, crachás, patrimônios e histórico: vazios.")
    print("Sala inicial: Sala de Informática")
    print("Login: secretaria@senai.br | Senha: senai123")


if __name__ == "__main__":
    inicializar_banco()
