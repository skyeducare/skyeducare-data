# SKY EDUCARE डेटा (अपने आप अपडेट)

यह repo हर 5 मिनट में अपने आप चलता है:

1. skyeducare.in (Classplus) से सारे कोर्स, दाम और छूट लाता है।
2. YouTube चैनल @SkyEducare से नए वीडियो लाता है।
3. नए कोर्स और वीडियो को अपने आप सही टीचर, कैटेगरी और कोर्स से जोड़ता है।
4. `data/live-data.json` बनाता है, जिसे skyeducare.com हर बार खुलते समय पढ़ती है।

## फ़ाइलें

- `data/live-data.json` : वेबसाइट यही पढ़ती है।
- `data/courses.json`, `data/blogs.json` : पूरा कच्चा डेटा।
- `data/status.json` : आख़िरी बदलाव कब हुआ और कोई गड़बड़ी तो नहीं।
- `overrides.json` : हाथ से किए बदलाव (जैसे किसी कोर्स का टीचर बदलना या कोई कोर्स छिपाना)। ये हर अपडेट के बाद भी बने रहते हैं।
- `scripts/sync.py` : अपडेट करने वाली script.

यह repo public है ताकि GitHub Actions पूरी तरह मुफ़्त रहें। इसमें कोई password या key नहीं है।
