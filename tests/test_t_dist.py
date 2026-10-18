"""Check the stdlib Student-t helpers in scripts/article_numbers.py against scipy.stats.t.

  analysis/state_dep/.venv-armT/bin/python -B tests/test_t_dist.py

The armT venv has scipy installed; article_numbers.py itself does not import it.
"""
import importlib.util
import os

from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("an", os.path.join(HERE, "..", "scripts", "article_numbers.py"))
an = importlib.util.module_from_spec(spec)
spec.loader.exec_module(an)

for df in (1, 2.5, 4, 7, 9.69, 30, 200):
    for t in (-6.0, -2.3, -0.4, 0.0, 0.7, 1.9, 2.365, 5.5):
        got, ref = an.t_cdf(t, df), stats.t.cdf(t, df)
        assert abs(got - ref) < 1e-10, ("cdf", df, t, got, ref)
    for p in (0.005, 0.025, 0.3, 0.5, 0.8, 0.975, 0.995):
        got, ref = an.t_ppf(p, df), stats.t.ppf(p, df)
        assert abs(got - ref) < 1e-6, ("ppf", df, p, got, ref)

assert abs(an.t_ppf(0.975, 7) - 2.364624251592785) < 1e-9
print("ALL ASSERTIONS PASSED")
