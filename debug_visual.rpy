init python:
    import json
    import os

    def espionar_cena(event, interact=True, **kwargs):
        if not interact or event != "show": return

        try:
            quem_fala = renpy.get_say_attributes()
            sprites = list(renpy.get_showing_tags("master"))
            
            # Tenta pegar o ID da tradução atual
            # (Isso é um hack avançado, nem sempre funciona, mas ajuda muito)
            id_linha = renpy.game.context().current_translate_id
            
            # Pega o texto que está sendo mostrado
            what = kwargs.get("what", "")

            estado = {
                "id_traducao": id_linha,
                "quem_fala": quem_fala,
                "texto_mostrado": what,
                "personagens_na_tela": sprites
            }

            caminho = os.path.join(config.basedir, "estado_visual.json")
            with open(caminho, "w") as f:
                json.dump(estado, f)
        except: pass

    config.character_callback = espionar_cena
