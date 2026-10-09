"""Superfície mínima de conta, só para o operador.

    python -m clareira.conta novo "Tev"     # cria um corpo e imprime o token
"""

import os
import sys

from .mundo import Mundo


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[0] != "novo":
        print(__doc__)
        return 1
    m = Mundo(os.environ.get("CLAREIRA_DB", "clareira.db"))
    c = m.novo_corpo(argv[1])
    print(f"corpo {c['id']} ({c['nome']})\ntoken {c['token']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
