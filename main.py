import pyjokes
def tell_joke(lang="en"):
    print(pyjokes.get_joke(language=lang))

if __name__=="__main__":
    lang = input("Choisissez une langue (en, de, es, it, gl):")
    tell_joke(lang)
