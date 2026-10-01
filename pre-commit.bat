py -m uv run --python 3.6 --with isort==5.10.1 -m isort --profile black --line-length 88 piexif tests setup.py
py -m uv run --python 3.14 --with isort==9.0.2 -m isort --profile black --line-length 88 debug
py -m uv run --python 3.6 --with black==21.12b0 -m black piexif tests setup.py
py -m uv run --python 3.14 --with black==26.5.1 -m black debug
py -m uv run --python 3.6 --with mypy==0.910 mypy --py2 piexif
py -m uv run --python 3.6 --with mypy==0.910 mypy piexif
py -V:2.7 -m flake8 .
py -V:3.5 -m flake8 .
