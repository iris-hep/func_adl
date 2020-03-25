.\.venv\3.7\Scripts\activate.ps1
Remove-Item -ErrorAction SilentlyContinue -Recurse ./dist/*
Remove-Item -ErrorAction SilentlyContinue -Recurse ./build/*
Remove-Item -ErrorAction SilentlyContinue -Recurse -Confirm:$false ./*.egg-info
python setup_func_adl.py sdist bdist_wheel
python setup_func_adl_ast.py sdist bdist_wheel
twine upload dist/*
Remove-Item -ErrorAction SilentlyContinue -Recurse ./dist/*
Remove-Item -ErrorAction SilentlyContinue -Recurse ./build/*
Remove-Item -ErrorAction SilentlyContinue -Recurse -Confirm:$false ./*.egg-info
