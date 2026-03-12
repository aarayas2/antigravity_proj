import os

for filename in ['tests/test_utils.py', 'tests/test_stockdatacache_coverage.py']:
    with open(filename, 'r') as f:
        content = f.read()

    # Replace global pandas.read_json patching with utils.pd.read_json
    content = content.replace("@patch('pandas.read_json')", "@patch('utils.pd.read_json')")
    
    # Replace global pandas.DataFrame.to_json patching with patch.object inside the function
    # In test_stockdatacache_coverage.py, it's a decorator. In test_utils.py, it's already a context manager.
    content = content.replace("@patch('pandas.DataFrame.to_json')", "@patch.object(pd.DataFrame, 'to_json')")
    
    # For context managers:
    content = content.replace("with patch('pandas.DataFrame.to_json')", "with patch.object(pd.DataFrame, 'to_json')")
    content = content.replace("with patch('pandas.read_json')", "with patch('utils.pd.read_json')")

    with open(filename, 'w') as f:
        f.write(content)
