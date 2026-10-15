"""Lanzador del repositorio; instale previamente el extra gui en el entorno virtual."""
if __name__ == '__main__':
    try:
        from micrograno_lab.app import main
    except ImportError:
        raise SystemExit('Instale primero: python -m pip install -c constraints.txt -e ".[gui]"')
    raise SystemExit(main())
