py -m uv run --python 3.6 --with isort==5.10.1 -m isort --profile black --line-length 88 piexif tests setup.py || exit /b 1
py -m uv run --python 3.14 --with isort==9.0.2 -m isort --profile black --line-length 88 debug || exit /b 1
py -m uv run --python 3.6 --with black==21.12b0 -m black piexif tests setup.py || exit /b 1
py -m uv run --python 3.14 --with black==26.5.1 -m black debug || exit /b 1
py -m uv run --python 3.6 --with mypy==0.910 -m mypy --py2 piexif || exit /b 1
py -m uv run --python 3.6 --with mypy==0.910 -m mypy piexif || exit /b 1

py -V:2.7 -m pip install flake8 || exit /b 1
py -V:2.7 -m pip install -r requirements.txt || exit /b 1
py -V:2.7 -m flake8 . --extend-exclude=debug || exit /b 1
py -V:2.7 setup.py test || exit /b 1

py -V:3.5 -m pip install flake8 || exit /b 1
py -V:3.5 -m pip install -r requirements.txt || exit /b 1
py -V:3.5 -m flake8 . --extend-exclude=debug || exit /b 1
py -V:3.5 setup.py test || exit /b 1
