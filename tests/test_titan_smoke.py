import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import titan_arena as ta


def smoke_test():
    print('Running TITAN smoke test...')
    tm = ta.TagManager()
    s = 'Hello {i} world\nNew line and \\layer_test[1]'
    m = tm.mascarar(s)
    assert '__T' in m, 'Tag masking failed'
    um = tm.desmascarar(m)
    assert 'Hello' in um and '\n' in um, 'Tag unmasking failed'

    eng = ta.TitanEngine()
    print('Annie test (headless):', eng.traduzir_annie('This is a test'))
    print('Google test (headless):', eng.traduzir_google_web('This is a test'))
    print('GPT test (headless):', eng.traduzir_gpt_web('This is a test', 'ctx'))
    score = eng.avaliar_judge('Hello world', 'Olá mundo')
    print('Judge heuristic score (headless):', score)
    assert isinstance(score, float), 'Judge did not return float'
    print('Smoke test completed successfully.')


if __name__ == '__main__':
    smoke_test()
