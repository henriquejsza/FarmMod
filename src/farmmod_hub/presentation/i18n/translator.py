from farmmod_hub.infrastructure.config import get_settings_store

_EN: dict[str, str] = {
    "Instalar Mods": "Install Mods",
    "Mods Instalados": "Installed Mods",
    "Instalar": "Install",
    "Instalados": "Installed",
    "Diagnostico": "Diagnostics",
    "Diagnostico de Log": "Log Diagnostics",
    "Acoes": "Actions",
    "Copiar diagnostico": "Copy diagnostics",
    "Exportar diagnostico": "Export diagnostics",
    "Diagnostico copiado": "Diagnostics copied",
    "O diagnostico foi copiado para a area de transferencia.": "The diagnostics were copied to the clipboard.",
    "Nao foi possivel exportar diagnostico": "Could not export diagnostics",
    "Diagnostico exportado": "Diagnostics exported",
    "Configurações": "Settings",
    "Nenhum mod instalado": "No mods installed",
    "Instale mods pela aba Instalar": "Install mods from the Install tab",
    "Resultado": "Result",
    "Avisos:": "Warnings:",
    "Nenhum mod processado.": "No mods processed.",
    "Erros:": "Errors:",
    "Arraste seus mods aqui para instalar": "Drag your mods here to install",
    "Aceita arquivos .zip ou pastas com modDesc.xml": "Accepts .zip files or folders with modDesc.xml",
    "Selecionar Arquivos": "Select Files",
    "Selecionar log.txt": "Select log.txt",
    "Arquivos de log (.txt)": "Log files (.txt)",
    "Selecionar Mods": "Select Mods",
    "Mods do FS19 (.zip)": "FS19 Mods (.zip)",
    "Todos os arquivos": "All files",
    "Instalando…": "Installing…",
    "Geral": "General",
    "Jogo": "Game",
    "Jogo ativo": "Active game",
    "Escolha qual Farming Simulator voce quer gerenciar": "Choose which Farming Simulator you want to manage",
    "Diretório de Mods": "Mods Directory",
    "Pasta onde os mods do FS19 são instalados": "Folder where FS19 mods are installed",
    "Pasta onde os mods do jogo selecionado sao instalados": "Folder where the selected game's mods are installed",
    "Perfis": "Profiles",
    "Coleções separadas para cada mapa/sessão": "Separate collections for each map/session",
    "Perfil ativo": "Active profile",
    "Gerenciar perfis": "Manage profiles",
    "Novo perfil": "New profile",
    "Remover perfil": "Remove profile",
    "Perfil": "Profile",
    "Backup de perfil": "Profile backup",
    "Exportar perfil ativo": "Export active profile",
    "Importar backup": "Import backup",
    "Salvar backup de perfil": "Save profile backup",
    "Arquivo de backup": "Backup file",
    "Backup exportado com sucesso.": "Backup exported successfully.",
    "Nao foi possivel exportar perfil.": "Could not export profile.",
    "Nao foi possivel importar backup.": "Could not import backup.",
    "Backup importado com sucesso.": "Backup imported successfully.",
    "Resumo": "Summary",
    "Mods suspeitos": "Suspicious mods",
    "Problemas gerais": "General issues",
    "Nenhum log analisado": "No log analyzed",
    "Nenhum mod suspeito encontrado": "No suspicious mods found",
    "Sem problemas gerais relevantes": "No relevant general issues",
    "Ver exemplos": "View examples",
    "Exemplos para": "Examples for",
    "Nao foi possivel analisar o log": "Could not analyze the log",
    "Abra o log.txt para encontrar mods suspeitos": "Open log.txt to find suspicious mods",
    "{errors} erros, {warnings} avisos": "{errors} errors, {warnings} warnings",
    "Não foi possível alterar perfil.": "Could not switch profile.",
    "Não foi possível criar perfil.": "Could not create profile.",
    "Não foi possível remover perfil.": "Could not remove profile.",
    "Pasta": "Folder",
    "Escolher pasta": "Choose folder",
    "Restaurar padrão": "Restore default",
    "Escolher pasta de mods": "Choose mods folder",
    "Idioma": "Language",
    "Idioma da interface": "Interface language",
    "Reiniciar o app": "Restart the app",
    "O idioma será aplicado após reiniciar o app.": "The language will be applied after restarting the app.",
    "Reiniciar": "Restart",
    "Agora não": "Not now",
    "Comportamento": "Behavior",
    "Confirmar exclusão": "Confirm deletion",
    "Pedir confirmação antes de excluir um mod": "Ask for confirmation before deleting a mod",
    "Excluir mod?": "Delete mod?",
    "Excluir": "Delete",
    "Cancelar": "Cancel",
    "será excluído permanentemente.": "will be permanently deleted.",
}


def _get_lang() -> str:
    return get_settings_store().get_language()


def _(text: str) -> str:
    if _get_lang() == "en":
        return _EN.get(text, text)
    return text


def count_label(n: int) -> str:
    if _get_lang() == "en":
        return f"{n} mod{'s' if n != 1 else ''} installed"
    s = "s" if n != 1 else ""
    return f"{n} mod{s} instalado{s}"


def installed_result(n: int) -> str:
    if _get_lang() == "en":
        return f"{n} mod(s) installed successfully."
    return f"{n} mod(s) instalado(s) com sucesso."


def updated_result(n: int) -> str:
    if _get_lang() == "en":
        return f"{n} mod(s) updated."
    return f"{n} mod(s) atualizado(s)."
