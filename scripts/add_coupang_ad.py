import runpy

# One-time maintenance wrapper: remove the current bottom 11 test ads.
runpy.run_path('scripts/remove_last_11_test_ads.py', run_name='__main__')
