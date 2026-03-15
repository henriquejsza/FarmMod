# FarmMod

![FarmMod logo](data/logo/io.github.henriquejsza.farmmod-hub.png)

Gerenciador de mods para Farming Simulator no Linux (Steam/Proton), com suporte a FS19, FS22 e FS25.

Idioma: Portugues (Brasil) | [English](README.md)

## Funcionalidades

- Instalacao por arrastar e soltar ou seletor de arquivos.
- Suporte a arquivos `.zip` e pastas de mod.
- Validacao antes de instalar (modDesc ausente, zip corrompido, nome invalido, conflito ZIP/pasta, e mais).
- Perfis por jogo (nao mistura mods entre FS19/FS22/FS25).
- Backup e restauracao de perfil com `.zip`.
- Diagnostico de `log.txt` com ranking de mods suspeitos.
- Interface disponivel em EN e PT-BR.

## Instalacao

Arch Linux (AUR via `yay`):

```bash
yay -S farmmod
```

Pagina do pacote: `https://aur.archlinux.org/packages/farmmod`

## Rodar Pelo Codigo-Fonte

Dependencias (Debian/Ubuntu):

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

Executar:

```bash
./run
```

Alternativa:

```bash
PYTHONPATH=src python3 -m farmmod_hub
```

## Desenvolvimento

Rodar testes:

```bash
pytest
```

## Licenca

AGPL-3.0-or-later. Veja `LICENSE`.

## Mantenedor

- Henrique
- GitHub: `@henriquejsza`
- E-mail: `henriquejsza@gmail.com`
