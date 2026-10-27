def strategy():
    words = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')
    return st.lists(st.sampled_from(words), min_size=1, max_size=10).flatmap(lambda ws: st.text(alphabet=' ', min_size=1, max_size=3).map(lambda sep: sep.join(ws))).flatmap(lambda s: st.text(alphabet=' ', min_size=0, max_size=3).map(lambda pre: pre + s)).flatmap(lambda s: st.text(alphabet=' ', min_size=0, max_size=3).map(lambda suf: s + suf)).filter(lambda s: s != s.strip() or '  ' in s).map(lambda s: (s,))
