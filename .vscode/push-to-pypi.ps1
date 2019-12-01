Remove-Item ./dist/*
python setup_func_adl.py sdist bdist_wheel
python setup_func_adl_ast.py sdist bdist_wheel
twine upload dist/*
