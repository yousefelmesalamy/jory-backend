"""The catalog dataset `manage.py seed_catalog` loads.

Kept apart from the command so neither file has to be read to understand the
other: this module is data only — no queries, no Django imports beyond the
choice enums it labels rows with. The command owns every write.

Variants are not written out one by one. A coffee declares the weights it is
sold in and the grinds it suits, and the loader takes the cartesian product,
scaling the price off `base_price` with the multipliers in `SIZES`. Writing
~420 SKUs by hand would bury the twenty numbers that actually differ.
"""

from decimal import Decimal

from apps.catalog.models import Grind, MachineType, Process, ProductType, RoastLevel

# (grams, price multiplier). The multiplier is deliberately sub-linear: 1kg
# costs 3.55x the 250g bag, not 4x, which is how bulk coffee is actually priced.
SIZES = ((250, Decimal("1.0")), (500, Decimal("1.9")), (1000, Decimal("3.55")))
# Green coffee is a bulk product — nobody buys 250g of unroasted beans.
GREEN_SIZES = ((1000, Decimal("1.0")), (5000, Decimal("4.6")))
# A gift set is one box at one price.
SET_SIZES = ((750, Decimal("1.0")),)

GRIND_CODES = {
    Grind.WHOLE_BEAN: "WB",
    Grind.ESPRESSO: "ES",
    Grind.FILTER: "FL",
    Grind.FRENCH_PRESS: "FP",
    Grind.TURKISH: "TK",
    "": "NA",
}

# Common grind sets, named so a coffee's intent reads at a glance.
FILTER_GRINDS = (Grind.WHOLE_BEAN, Grind.FILTER, Grind.FRENCH_PRESS)
ESPRESSO_GRINDS = (Grind.WHOLE_BEAN, Grind.ESPRESSO)
ALL_ROUND_GRINDS = (Grind.WHOLE_BEAN, Grind.ESPRESSO, Grind.FILTER)
TURKISH_GRINDS = (Grind.TURKISH, Grind.WHOLE_BEAN)
NO_GRIND = ("",)


# --- Taxonomy ----------------------------------------------------------------

# (name, name_ar, product_type, description, [(child, child_ar, child_desc)])
# Only roots carry a type; children inherit it via effective_product_type.
CATEGORIES = [
    (
        "Coffee",
        "قهوة",
        ProductType.COFFEE,
        "Roasted to order in Cairo, shipped within 48 hours of the roast date.",
        "محمصة عند الطلب في القاهرة، وتُشحن خلال 48 ساعة من تاريخ التحميص.",
        [
            (
                "Single Origin",
                "أصل واحد",
                "Traceable lots from one farm, washing station or co-operative.",
                "محاصيل من مزرعة أو محطة غسيل أو جمعية تعاونية واحدة.",
            ),
            (
                "Signature Blends",
                "خلطات جوري",
                "Our own blends, built for balance in milk and black alike.",
                "خلطاتنا الخاصة، متوازنة مع الحليب وبدونه.",
            ),
            (
                "Espresso Blends",
                "خلطات إسبريسو",
                "Dialled for pressure: sweet, heavy-bodied and forgiving on the bar.",
                "مصممة للضغط: حلاوة وقوام ثقيل وثبات على ماكينة الإسبريسو.",
            ),
            (
                "Flavored Coffee",
                "قهوة بنكهات",
                "Arabica infused after the roast — never a syrup, never a filler.",
                "أرابيكا تُنكّه بعد التحميص — بلا شراب ولا إضافات مالئة.",
            ),
            (
                "Turkish & Arabic",
                "قهوة تركي وعربي",
                "Fine-ground Turkish and light Gulf-style qahwa with cardamom.",
                "تركي مطحون ناعم وقهوة عربية فاتحة التحميص بالهيل.",
            ),
            (
                "Decaf",
                "منزوعة الكافيين",
                "Swiss Water and sugarcane decaffeination — flavour kept, caffeine gone.",
                "نزع الكافيين بطريقة الماء السويسري وقصب السكر — النكهة تبقى.",
            ),
            (
                "Green Beans",
                "بن أخضر",
                "Unroasted lots by the kilo, for home and shop roasters.",
                "بن غير محمص بالكيلو، لمحامص المنزل والمحل.",
            ),
            (
                "Sampler & Gift Sets",
                "علب التذوق والهدايا",
                "Curated boxes — the easiest way to find what you like.",
                "علب مختارة — أسهل طريقة لتكتشف ما يعجبك.",
            ),
        ],
    ),
    (
        "Equipment",
        "معدات",
        ProductType.EQUIPMENT,
        "Grinders, brewers and kettles we use on our own bar.",
        "مطاحن وأدوات تحضير وغلايات نستخدمها في مقهانا.",
        [
            ("Grinders", "مطاحن", "Burr grinders for filter and espresso.",
             "مطاحن بأقراص للفلتر والإسبريسو."),
            ("Brewers & Drippers", "أدوات التحضير", "Pour-over, immersion and carafes.",
             "التقطير اليدوي والنقع والدوارق."),
            ("Kettles", "غلايات", "Gooseneck kettles with temperature control.",
             "غلايات بعنق إوزة مع تحكم في الحرارة."),
            ("Accessories", "إكسسوارات", "Scales, canisters and the small things.",
             "موازين وعلب حفظ والتفاصيل الصغيرة."),
        ],
    ),
    (
        "Roasting Machines",
        "محامص",
        ProductType.ROASTING_MACHINE,
        "Drum roasters for the kitchen counter and the roastery floor.",
        "محامص أسطوانية لمطبخ المنزل ولأرضية المحمصة.",
        [
            ("Home Roasters", "محامص منزلية", "Sub-kilo batches for the enthusiast.",
             "دفعات أقل من كيلو لهواة التحميص."),
            ("Shop Roasters", "محامص تجارية", "6kg and up, for production.",
             "من 6 كجم فأعلى، للإنتاج التجاري."),
        ],
    ),
]

# (name, name_ar) — the lookup table behind the `origin` filter facet.
ORIGINS = [
    ("Ethiopia", "إثيوبيا"),
    ("Kenya", "كينيا"),
    ("Yemen", "اليمن"),
    ("Colombia", "كولومبيا"),
    ("Brazil", "البرازيل"),
    ("Guatemala", "غواتيمالا"),
    ("Costa Rica", "كوستاريكا"),
    ("Rwanda", "رواندا"),
    ("Burundi", "بوروندي"),
    ("Indonesia", "إندونيسيا"),
    ("Panama", "بنما"),
    ("Peru", "بيرو"),
    ("Honduras", "هندوراس"),
    ("Tanzania", "تنزانيا"),
    ("India", "الهند"),
    ("Uganda", "أوغندا"),
    # Blends are multi-origin by definition. One row, so a blend still answers
    # the origin facet instead of dropping out of it.
    ("Multi-Origin", "أصول متعددة"),
]

FLAVORS = [
    ("Vanilla", "فانيليا"),
    ("Hazelnut", "بندق"),
    ("Salted Caramel", "كراميل مملح"),
    ("Chocolate", "شوكولاتة"),
    ("Cinnamon", "قرفة"),
    ("Cardamom", "هيل"),
    ("Coconut", "جوز الهند"),
    ("Irish Cream", "آيرش كريم"),
    ("Mint", "نعناع"),
    ("Saffron", "زعفران"),
]

# (name, country, bio, bio_ar)
ROASTERS = [
    (
        "Jory Roastery",
        "Egypt",
        "Our own roastery in Cairo. Small drum batches, roasted to order.",
        "محمصتنا في القاهرة. دفعات صغيرة على أسطوانة، تُحمّص عند الطلب.",
    ),
    (
        "Nile Coffee Co.",
        "Egypt",
        "Specialty roasters working direct with East African washing stations.",
        "محمصة متخصصة تتعامل مباشرة مع محطات الغسيل في شرق أفريقيا.",
    ),
    (
        "Red Sea Roasters",
        "Egypt",
        "Port Said roastery with a long line in Yemeni and Ethiopian naturals.",
        "محمصة في بورسعيد لها باع طويل في البن اليمني والإثيوبي الطبيعي.",
    ),
    (
        "Cairo Bean Works",
        "Egypt",
        "A Maadi micro-roastery focused on espresso for the local bar trade.",
        "محمصة صغيرة في المعادي متخصصة في إسبريسو المقاهي المحلية.",
    ),
]

# (name, name_ar, country)
BRANDS = [
    ("Probat", "بروبات", "Germany"),
    ("Giesen", "جيزن", "Netherlands"),
    ("Hario", "هاريو", "Japan"),
    ("Fellow", "فيلو", "United States"),
    ("Baratza", "باراتزا", "United States"),
    ("Chemex", "كيمكس", "United States"),
]


# --- Coffee ------------------------------------------------------------------
#
# `code` becomes the SKU stem and must be unique. `base_price` is the 250g
# whole-bean price in EGP; every other SKU scales off it. `sale` marks the
# product down — the loader derives compare_at_price from it, so the DB check
# constraint (compare_at > price) can never be violated by a typo here.

COFFEES = [
    # --- Single Origin -------------------------------------------------------
    {
        "code": "ETH-YRG",
        "name": "Ethiopia Yirgacheffe G1",
        "name_ar": "إثيوبيا يرجاتشيف جي1",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("340"),
        "grinds": FILTER_GRINDS,
        "stock": 60,
        "featured": True,
        "short_description": "Floral and bright — jasmine, lemon and black tea.",
        "short_description_ar": "عطرية ومنعشة — ياسمين وليمون وشاي أسود.",
        "description": (
            "A washed Grade 1 lot from the Gedeo zone, dried on raised beds and "
            "roasted light to keep the florals intact. It brews clean and tea-like; "
            "give it a coarser grind and cooler water than you think it needs."
        ),
        "description_ar": (
            "محصول مغسول من الدرجة الأولى من منطقة جيديو، جُفف على أسِرّة مرتفعة "
            "وحُمّص تحميصاً فاتحاً للحفاظ على رائحته الزهرية. مذاقه نظيف يشبه الشاي؛ "
            "استخدم طحنة أخشن وماءً أبرد مما تظن."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Yirgacheffe, Gedeo",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1950,
            "tasting_notes": "Jasmine, lemon, black tea",
            "tasting_notes_ar": "ياسمين، ليمون، شاي أسود",
            "harvest_year": 2025,
            "cupping_score": Decimal("87.5"),
        },
    },
    {
        "code": "ETH-GUJ",
        "name": "Ethiopia Sidamo Guji",
        "name_ar": "إثيوبيا سيدامو جوجي",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("355"),
        "grinds": FILTER_GRINDS,
        "stock": 45,
        "featured": True,
        "short_description": "Natural process — blueberry, cocoa and a syrupy body.",
        "short_description_ar": "معالجة طبيعية — توت أزرق وكاكاو وقوام كثيف.",
        "description": (
            "Dried in the cherry for eighteen days, which is where the blueberry "
            "comes from. Heavier and sweeter than a washed Ethiopian, and the one "
            "we hand people who say they don't like light roasts."
        ),
        "description_ar": (
            "جُفف داخل الثمرة لمدة ثمانية عشر يوماً، ومن هنا يأتي طعم التوت الأزرق. "
            "أثقل وأحلى من الإثيوبي المغسول، وهو ما نقدمه لمن يقول إنه لا يحب "
            "التحميص الفاتح."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Guji, Sidamo",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 2050,
            "tasting_notes": "Blueberry, cocoa nib, ripe apricot",
            "tasting_notes_ar": "توت أزرق، حبيبات كاكاو، مشمش ناضج",
            "harvest_year": 2025,
            "cupping_score": Decimal("88.0"),
        },
    },
    {
        "code": "ETH-HRR",
        "name": "Ethiopia Harrar Longberry",
        "name_ar": "إثيوبيا حرر لونج بيري",
        "category": "Single Origin",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("320"),
        "grinds": FILTER_GRINDS,
        "stock": 30,
        "short_description": "Wild and winey, with blackberry and dried fig.",
        "short_description_ar": "جامحة وخمرية، بطعم التوت الأسود والتين المجفف.",
        "description": (
            "One of the oldest coffees in trade, still sun-dried on patios in the "
            "eastern highlands. Rustic rather than clean — expect fruit that leans "
            "fermented, in the best way."
        ),
        "description_ar": (
            "من أقدم أنواع البن في التجارة، ولا يزال يُجفف تحت الشمس في مرتفعات "
            "الشرق. طابعه ريفي لا نظيف — توقع فاكهة تميل إلى التخمر، بأفضل معنى."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Harrar, Oromia",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1800,
            "tasting_notes": "Blackberry, dried fig, red wine",
            "tasting_notes_ar": "توت أسود، تين مجفف، نبيذ أحمر",
            "harvest_year": 2025,
            "cupping_score": Decimal("85.5"),
        },
    },
    {
        "code": "KEN-AA",
        "name": "Kenya AA Nyeri",
        "name_ar": "كينيا AA نييري",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("380"),
        "grinds": FILTER_GRINDS,
        "stock": 40,
        "featured": True,
        "short_description": "Blackcurrant and grapefruit over a hard, bright acidity.",
        "short_description_ar": "كشمش أسود وجريب فروت فوق حموضة حادة ومنعشة.",
        "description": (
            "AA is the screen size, not the grade of the cup — but in Nyeri the two "
            "tend to arrive together. Double-washed and fermented under water, which "
            "is what gives Kenyan coffee that blackcurrant snap."
        ),
        "description_ar": (
            "AA هي مقاس الحبة لا درجة المذاق — لكنهما في نييري يأتيان معاً عادة. "
            "مغسولة مرتين ومخمّرة تحت الماء، وهذا سر حدة الكشمش الأسود في البن الكيني."
        ),
        "profile": {
            "origin": "Kenya",
            "region": "Nyeri, Central Province",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1750,
            "tasting_notes": "Blackcurrant, grapefruit, brown sugar",
            "tasting_notes_ar": "كشمش أسود، جريب فروت، سكر بني",
            "harvest_year": 2025,
            "cupping_score": Decimal("88.5"),
        },
    },
    {
        "code": "KEN-PB",
        "name": "Kenya Kirinyaga Peaberry",
        "name_ar": "كينيا كيرينياغا بيبيري",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("400"),
        "grinds": FILTER_GRINDS,
        "stock": 22,
        "short_description": "The single-bean cherries, sorted out — denser and sweeter.",
        "short_description_ar": "حبات مفردة مفرزة يدوياً — أكثف وأحلى.",
        "description": (
            "Peaberry is the roughly five percent of cherries that grow one round "
            "bean instead of two flat ones. Sorted out and roasted separately because "
            "they take heat differently. Concentrated, with more sugar than the AA."
        ),
        "description_ar": (
            "البيبيري هو نحو خمسة بالمئة من الثمار التي تنتج حبة واحدة مستديرة بدل "
            "حبتين مسطحتين. تُفرز وتُحمص على حدة لأنها تستقبل الحرارة بشكل مختلف. "
            "مركّزة، وأحلى من الـ AA."
        ),
        "profile": {
            "origin": "Kenya",
            "region": "Kirinyaga",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1800,
            "tasting_notes": "Plum, cane sugar, tomato leaf",
            "tasting_notes_ar": "برقوق، سكر قصب، ورق طماطم",
            "harvest_year": 2025,
            "cupping_score": Decimal("88.0"),
        },
    },
    {
        "code": "YEM-MTR",
        "name": "Yemen Mocha Matari",
        "name_ar": "يمني موكا مطري",
        "category": "Single Origin",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("620"),
        "grinds": FILTER_GRINDS,
        "stock": 15,
        "featured": True,
        "sale": True,
        "short_description": "The original mocha — dried fruit, cardamom and dark chocolate.",
        "short_description_ar": "الموكا الأصلية — فاكهة مجففة وهيل وشوكولاتة داكنة.",
        "description": (
            "From the Bani Matar terraces west of Sana'a, farmed at altitude on plots "
            "measured in metres rather than hectares. Small, irregular beans and an "
            "unmistakable wine-and-spice cup. Quantities are genuinely limited."
        ),
        "description_ar": (
            "من مدرجات بني مطر غرب صنعاء، تُزرع على ارتفاعات عالية في قطع أرض تُقاس "
            "بالأمتار لا بالهكتارات. حبات صغيرة غير منتظمة ومذاق لا يُخطئ من التوابل "
            "والنبيذ. الكميات محدودة فعلاً."
        ),
        "profile": {
            "origin": "Yemen",
            "region": "Bani Matar, Sana'a",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 2200,
            "tasting_notes": "Dried fruit, cardamom, dark chocolate",
            "tasting_notes_ar": "فاكهة مجففة، هيل، شوكولاتة داكنة",
            "harvest_year": 2025,
            "cupping_score": Decimal("89.0"),
        },
    },
    {
        "code": "YEM-HRZ",
        "name": "Yemen Haraz Heirloom",
        "name_ar": "يمني حراز",
        "category": "Single Origin",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("580"),
        "grinds": FILTER_GRINDS,
        "stock": 12,
        "short_description": "Heirloom varietals from the Haraz mountains — spiced and dense.",
        "short_description_ar": "أصناف موروثة من جبال حراز — متبّلة وكثيفة.",
        "description": (
            "Haraz sits at the western edge of the Yemeni highlands and its trees are "
            "descended from stock that predates the trade. Roasted a touch darker to "
            "settle the spice."
        ),
        "description_ar": (
            "تقع حراز على الطرف الغربي للمرتفعات اليمنية، وأشجارها تنحدر من سلالات "
            "أقدم من تجارة البن نفسها. نحمصها أغمق قليلاً لتهدئة حدة التوابل."
        ),
        "profile": {
            "origin": "Yemen",
            "region": "Haraz",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 2100,
            "tasting_notes": "Clove, raisin, cocoa",
            "tasting_notes_ar": "قرنفل، زبيب، كاكاو",
            "harvest_year": 2025,
            "cupping_score": Decimal("87.0"),
        },
    },
    {
        "code": "COL-HUI",
        "name": "Colombia Huila Supremo",
        "name_ar": "كولومبيا هويلا سوبريمو",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("300"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 80,
        "short_description": "Caramel, red apple and a clean finish. The easy one.",
        "short_description_ar": "كراميل وتفاح أحمر ونهاية نظيفة. الخيار السهل.",
        "description": (
            "If you are buying coffee for a household that disagrees about coffee, "
            "buy this. Balanced, sweet, no sharp edges, and it takes milk without "
            "disappearing."
        ),
        "description_ar": (
            "إن كنت تشتري بناً لبيت لا يتفق أهله على القهوة، فاشترِ هذا. متوازن وحلو "
            "بلا حواف حادة، ولا يختفي مع الحليب."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1700,
            "tasting_notes": "Caramel, red apple, almond",
            "tasting_notes_ar": "كراميل، تفاح أحمر، لوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.5"),
        },
    },
    {
        "code": "COL-NAR",
        "name": "Colombia Nariño Washed",
        "name_ar": "كولومبيا نارينيو المغسولة",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("310"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 55,
        "short_description": "Higher, brighter Colombia — citrus over panela sweetness.",
        "short_description_ar": "كولومبيا أعلى وأنصع — حمضيات فوق حلاوة البانيلا.",
        "description": (
            "Nariño's farms sit near the Ecuadorian border at altitudes that slow the "
            "cherry down. The result is more acidity and more sugar than you expect "
            "from Colombia."
        ),
        "description_ar": (
            "تقع مزارع نارينيو قرب الحدود الإكوادورية على ارتفاعات تُبطئ نضج الثمرة، "
            "فتأتي بحموضة وحلاوة أعلى مما تتوقعه من كولومبيا."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Nariño",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 2000,
            "tasting_notes": "Orange, panela, milk chocolate",
            "tasting_notes_ar": "برتقال، بانيلا، شوكولاتة بالحليب",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.0"),
        },
    },
    {
        "code": "BRA-CER",
        "name": "Brazil Cerrado Mineiro",
        "name_ar": "برازيل سيرادو مينيرو",
        "category": "Single Origin",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("250"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 120,
        "short_description": "Peanut, milk chocolate, low acidity. Built for espresso.",
        "short_description_ar": "فول سوداني وشوكولاتة بالحليب وحموضة منخفضة. للإسبريسو.",
        "description": (
            "The workhorse. Cerrado's flat, mechanised farms produce consistent, "
            "nutty coffee at a price that makes it the base of half the espresso in "
            "the world, ours included."
        ),
        "description_ar": (
            "حصان العمل. مزارع سيرادو المستوية والمميكنة تنتج بناً ثابت الجودة بطعم "
            "المكسرات وبسعر يجعله أساس نصف الإسبريسو في العالم، ومنه إسبريسونا."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro, Minas Gerais",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1100,
            "tasting_notes": "Peanut, milk chocolate, malt",
            "tasting_notes_ar": "فول سوداني، شوكولاتة بالحليب، شعير",
            "harvest_year": 2025,
            "cupping_score": Decimal("82.5"),
        },
    },
    {
        "code": "BRA-MOG",
        "name": "Brazil Mogiana Natural",
        "name_ar": "برازيل موجيانا الطبيعية",
        "category": "Single Origin",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("260"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 90,
        "short_description": "Heavier and sweeter than Cerrado — hazelnut and toffee.",
        "short_description_ar": "أثقل وأحلى من سيرادو — بندق وتوفي.",
        "description": (
            "Mogiana's red soil and older trees give a rounder cup than the Cerrado "
            "next door. Very low acidity, which is why it holds up under milk and "
            "sugar without turning thin."
        ),
        "description_ar": (
            "تربة موجيانا الحمراء وأشجارها الأقدم تعطي مذاقاً أكثر استدارة من سيرادو "
            "المجاورة. حموضتها منخفضة جداً، ولهذا تصمد مع الحليب والسكر دون أن ترق."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Mogiana, São Paulo",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1200,
            "tasting_notes": "Hazelnut, toffee, baked bread",
            "tasting_notes_ar": "بندق، توفي، خبز مخبوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.0"),
        },
    },
    {
        "code": "GTM-ANT",
        "name": "Guatemala Antigua",
        "name_ar": "غواتيمالا أنتيغوا",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("315"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 50,
        "short_description": "Volcanic-soil classic — cocoa, orange peel and pipe smoke.",
        "short_description_ar": "كلاسيكية التربة البركانية — كاكاو وقشر برتقال ودخان.",
        "description": (
            "Grown in a valley ringed by three volcanoes, which trap the ash that "
            "gives Antigua its body. A benchmark coffee: if you want to know what "
            "'balanced' means, this is the reference."
        ),
        "description_ar": (
            "تُزرع في واد تحيط به ثلاثة براكين تحبس الرماد الذي يمنح أنتيغوا قوامها. "
            "بن مرجعي: إن أردت أن تعرف معنى «التوازن»، فهذا هو المقياس."
        ),
        "profile": {
            "origin": "Guatemala",
            "region": "Antigua",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1600,
            "tasting_notes": "Cocoa, orange peel, toasted almond",
            "tasting_notes_ar": "كاكاو، قشر برتقال، لوز محمص",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.5"),
        },
    },
    {
        "code": "CRI-TAR",
        "name": "Costa Rica Tarrazú",
        "name_ar": "كوستاريكا تاراسو",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("330"),
        "grinds": FILTER_GRINDS,
        "stock": 38,
        "short_description": "Honey process — apricot, honey and a syrupy weight.",
        "short_description_ar": "معالجة بالعسل — مشمش وعسل وقوام كثيف.",
        "description": (
            "Honey processing leaves some of the sticky mucilage on the bean while it "
            "dries, landing between washed clarity and natural sweetness. Tarrazú's "
            "altitude does the rest."
        ),
        "description_ar": (
            "المعالجة بالعسل تُبقي جزءاً من اللب اللزج على الحبة أثناء التجفيف، "
            "فتقع بين نقاء المغسول وحلاوة الطبيعي. وارتفاع تاراسو يفعل الباقي."
        ),
        "profile": {
            "origin": "Costa Rica",
            "region": "Tarrazú",
            "process": Process.HONEY,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1750,
            "tasting_notes": "Apricot, honey, cane sugar",
            "tasting_notes_ar": "مشمش، عسل، سكر قصب",
            "harvest_year": 2025,
            "cupping_score": Decimal("87.0"),
        },
    },
    {
        "code": "RWA-NYA",
        "name": "Rwanda Nyamasheke",
        "name_ar": "رواندا نياماشيكي",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("325"),
        "grinds": FILTER_GRINDS,
        "stock": 34,
        "short_description": "Red berries and a tea-like body from Lake Kivu's hills.",
        "short_description_ar": "توت أحمر وقوام يشبه الشاي من تلال بحيرة كيفو.",
        "description": (
            "Bourbon varietals on the steep hills above Lake Kivu, processed at a "
            "co-operative washing station within hours of picking. Delicate and "
            "floral — treat it like an Ethiopian."
        ),
        "description_ar": (
            "أصناف بوربون على التلال المنحدرة فوق بحيرة كيفو، تُعالج في محطة غسيل "
            "تعاونية خلال ساعات من القطف. رقيقة وزهرية — تعامل معها كبن إثيوبي."
        ),
        "profile": {
            "origin": "Rwanda",
            "region": "Nyamasheke, Western Province",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1900,
            "tasting_notes": "Red berries, orange blossom, black tea",
            "tasting_notes_ar": "توت أحمر، زهر برتقال، شاي أسود",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.5"),
        },
    },
    {
        "code": "BDI-KAY",
        "name": "Burundi Kayanza",
        "name_ar": "بوروندي كايانزا",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("320"),
        "grinds": FILTER_GRINDS,
        "stock": 28,
        "short_description": "Grapefruit and blackcurrant, lighter on its feet than Kenya.",
        "short_description_ar": "جريب فروت وكشمش أسود، أخف من الكيني.",
        "description": (
            "Burundi's smallholders average a few hundred trees each, so a lot is "
            "really a village. Kayanza's cup runs close to Kenya's but with less "
            "weight and a softer acidity."
        ),
        "description_ar": (
            "متوسط ما يملكه صغار المزارعين في بوروندي بضع مئات من الأشجار، فالمحصول "
            "الواحد قرية كاملة. مذاق كايانزا قريب من الكيني لكن بوزن أقل وحموضة ألين."
        ),
        "profile": {
            "origin": "Burundi",
            "region": "Kayanza",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1800,
            "tasting_notes": "Grapefruit, blackcurrant, honey",
            "tasting_notes_ar": "جريب فروت، كشمش أسود، عسل",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.0"),
        },
    },
    {
        "code": "IDN-MAN",
        "name": "Sumatra Mandheling",
        "name_ar": "سومطرة مانديلينج",
        "category": "Single Origin",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("335"),
        "grinds": FILTER_GRINDS,
        "stock": 42,
        "short_description": "Wet-hulled and earthy — cedar, tobacco and dark chocolate.",
        "short_description_ar": "مقشورة رطبة وترابية — أرز وتبغ وشوكولاتة داكنة.",
        "description": (
            "Wet-hulling is unique to Indonesia: the parchment comes off while the "
            "bean is still wet, which kills acidity and builds body. Divisive and "
            "worth trying — nothing else tastes like it."
        ),
        "description_ar": (
            "التقشير الرطب طريقة إندونيسية خالصة: يُزال الغلاف والحبة ما زالت رطبة، "
            "فتنخفض الحموضة ويزداد القوام. مثيرة للجدل وتستحق التجربة — لا شيء آخر "
            "بمذاقها."
        ),
        "profile": {
            "origin": "Indonesia",
            "region": "Lake Toba, North Sumatra",
            "process": Process.WET_HULLED,
            "roast_level": RoastLevel.DARK,
            "altitude_masl": 1400,
            "tasting_notes": "Cedar, tobacco, dark chocolate",
            "tasting_notes_ar": "خشب أرز، تبغ، شوكولاتة داكنة",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.0"),
        },
    },
    {
        "code": "PAN-GEI",
        "name": "Panama Boquete Geisha",
        "name_ar": "بنما بوكيتي جيشا",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("950"),
        "grinds": (Grind.WHOLE_BEAN, Grind.FILTER),
        "stock": 8,
        "featured": True,
        "short_description": "The famous one — jasmine, bergamot and peach. Micro-lot.",
        "short_description_ar": "الأشهر على الإطلاق — ياسمين وبرغموت وخوخ. محصول دقيق.",
        "description": (
            "Geisha put Panama on the specialty map and still sets the auction "
            "records. Grown at 1,650m in Boquete, roasted very light, and honestly "
            "closer to a floral tea than to what most people mean by coffee. "
            "Eight kilos in total."
        ),
        "description_ar": (
            "الجيشا هي التي وضعت بنما على خريطة القهوة المختصة، وما زالت تحطم أرقام "
            "المزادات. تُزرع على ارتفاع 1650 متراً في بوكيتي، وتُحمص فاتحة جداً، وهي "
            "بصراحة أقرب إلى شاي زهري منها إلى ما يقصده الناس بالقهوة. ثمانية كيلوات فقط."
        ),
        "profile": {
            "origin": "Panama",
            "region": "Boquete, Chiriquí",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1650,
            "tasting_notes": "Jasmine, bergamot, white peach",
            "tasting_notes_ar": "ياسمين، برغموت، خوخ أبيض",
            "harvest_year": 2025,
            "cupping_score": Decimal("92.0"),
        },
    },
    {
        "code": "PER-CAJ",
        "name": "Peru Cajamarca Organic",
        "name_ar": "بيرو كاخاماركا العضوية",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "base_price": Decimal("295"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 60,
        "short_description": "Certified organic — soft, nutty and very easy to drink.",
        "short_description_ar": "عضوية معتمدة — ناعمة بطعم المكسرات وسهلة الشرب.",
        "description": (
            "Cajamarca's co-operatives were organic long before anyone was paying for "
            "the certificate. A gentle, low-acid cup that suits a French press and a "
            "slow morning."
        ),
        "description_ar": (
            "كانت تعاونيات كاخاماركا عضوية قبل أن يدفع أحد ثمن الشهادة بزمن. مذاق "
            "لطيف قليل الحموضة يناسب الفرنش برس وصباحاً بطيئاً."
        ),
        "profile": {
            "origin": "Peru",
            "region": "Cajamarca",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1750,
            "tasting_notes": "Walnut, cocoa, soft citrus",
            "tasting_notes_ar": "جوز، كاكاو، حمضيات خفيفة",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.0"),
        },
    },
    {
        "code": "HND-MAR",
        "name": "Honduras Marcala",
        "name_ar": "هندوراس ماركالا",
        "category": "Single Origin",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("285"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 65,
        "short_description": "Caramel and stone fruit at a price that undersells it.",
        "short_description_ar": "كراميل وفاكهة ذات نواة بسعر أقل مما تستحق.",
        "description": (
            "Marcala was Honduras's first protected denomination of origin. Central "
            "American structure without the Guatemalan price tag — the value pick of "
            "the single origins."
        ),
        "description_ar": (
            "ماركالا أول تسمية منشأ محمية في هندوراس. بنية أمريكا الوسطى بلا سعر "
            "غواتيمالا — أفضل قيمة بين بن الأصل الواحد."
        ),
        "profile": {
            "origin": "Honduras",
            "region": "Marcala, La Paz",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1500,
            "tasting_notes": "Caramel, peach, hazelnut",
            "tasting_notes_ar": "كراميل، خوخ، بندق",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.5"),
        },
    },
    {
        "code": "TZA-PB",
        "name": "Tanzania Kilimanjaro Peaberry",
        "name_ar": "تنزانيا كليمنجارو بيبيري",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("345"),
        "grinds": FILTER_GRINDS,
        "stock": 26,
        "short_description": "Bright and juicy — blackberry, lime and cocoa.",
        "short_description_ar": "منعشة وعصيرية — توت أسود وليمون أخضر وكاكاو.",
        "description": (
            "Grown on the southern slopes of Kilimanjaro and sorted for peaberry. "
            "Sits between Kenya's intensity and Rwanda's delicacy, with a juiciness "
            "that carries through an iced brew."
        ),
        "description_ar": (
            "تُزرع على المنحدرات الجنوبية لكليمنجارو وتُفرز للبيبيري. تقع بين حدة "
            "الكيني ورقة الرواندي، بعصيرية تظهر بوضوح في التحضير البارد."
        ),
        "profile": {
            "origin": "Tanzania",
            "region": "Kilimanjaro",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1700,
            "tasting_notes": "Blackberry, lime, cocoa",
            "tasting_notes_ar": "توت أسود، ليمون أخضر، كاكاو",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.0"),
        },
    },

    # --- Signature Blends ----------------------------------------------------
    {
        "code": "BLD-HSE",
        "name": "Jory House Blend",
        "name_ar": "خلطة جوري الأساسية",
        "category": "Signature Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("265"),
        "grinds": (Grind.WHOLE_BEAN, Grind.ESPRESSO, Grind.FILTER, Grind.FRENCH_PRESS),
        "stock": 200,
        "featured": True,
        "short_description": "Brazil, Colombia and Ethiopia. Our everyday cup since day one.",
        "short_description_ar": "برازيل وكولومبيا وإثيوبيا. فنجاننا اليومي منذ البداية.",
        "description": (
            "Sixty percent Brazil for body, thirty Colombia for sweetness, ten "
            "Ethiopia for lift. It works black, it works in milk, and it is the "
            "coffee we drink at the roastery."
        ),
        "description_ar": (
            "ستون بالمئة برازيل للقوام، وثلاثون كولومبيا للحلاوة، وعشرة إثيوبيا "
            "للانتعاش. تعمل سادة، وتعمل مع الحليب، وهي القهوة التي نشربها في المحمصة."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Colombia / Ethiopia",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Milk chocolate, almond, red apple",
            "tasting_notes_ar": "شوكولاتة بالحليب، لوز، تفاح أحمر",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.0"),
        },
    },
    {
        "code": "BLD-MRN",
        "name": "Jory Morning Blend",
        "name_ar": "خلطة الصباح",
        "category": "Signature Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("255"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 150,
        "short_description": "Lighter and brighter — the one to wake up on.",
        "short_description_ar": "أفتح وأنعش — خلطة الاستيقاظ.",
        "description": (
            "Weighted toward Central America and roasted a shade lighter than the "
            "House. Citrus up front, sweet in the middle, gone clean by the finish."
        ),
        "description_ar": (
            "تميل إلى بن أمريكا الوسطى وتُحمص أفتح بدرجة من الخلطة الأساسية. حمضيات "
            "في البداية، وحلاوة في الوسط، ونهاية نظيفة."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Guatemala / Honduras / Ethiopia",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Orange, honey, toasted nut",
            "tasting_notes_ar": "برتقال، عسل، مكسرات محمصة",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.5"),
        },
    },
    {
        "code": "BLD-CRO",
        "name": "Cairo Nights Blend",
        "name_ar": "خلطة ليالي القاهرة",
        "category": "Signature Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("270"),
        "grinds": (Grind.WHOLE_BEAN, Grind.ESPRESSO, Grind.FRENCH_PRESS),
        "stock": 110,
        "sale": True,
        "short_description": "Dark, sweet and heavy. Made for after midnight.",
        "short_description_ar": "داكنة وحلوة وثقيلة. لما بعد منتصف الليل.",
        "description": (
            "A dark roast that stops just short of bitter — molasses and dark cocoa, "
            "with enough body to stand up to sugar and a long conversation."
        ),
        "description_ar": (
            "تحميص داكن يقف قبل المرارة بخطوة — دبس وكاكاو داكن، بقوام يكفي ليصمد "
            "أمام السكر وحديث طويل."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Sumatra",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Molasses, dark cocoa, walnut",
            "tasting_notes_ar": "دبس، كاكاو داكن، جوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.0"),
        },
    },
    {
        "code": "BLD-NIL",
        "name": "Nile Valley Blend",
        "name_ar": "خلطة وادي النيل",
        "category": "Signature Blends",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("280"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 95,
        "short_description": "East African throughout — berries, florals and a clean body.",
        "short_description_ar": "شرق أفريقية بالكامل — توت وزهور وقوام نظيف.",
        "description": (
            "Ethiopia and Kenya in equal parts, with a little Rwanda to soften the "
            "join. Bright, fruit-forward and best without milk."
        ),
        "description_ar": (
            "إثيوبيا وكينيا بنسب متساوية، مع قليل من رواندا لتنعيم الالتقاء. منعشة "
            "وفاكهية، وأفضل ما تكون بدون حليب."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Ethiopia / Kenya / Rwanda",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Berries, jasmine, citrus",
            "tasting_notes_ar": "توت، ياسمين، حمضيات",
            "harvest_year": 2025,
            "cupping_score": Decimal("86.5"),
        },
    },
    {
        "code": "BLD-SUN",
        "name": "Sunrise Breakfast Blend",
        "name_ar": "خلطة إفطار الشروق",
        "category": "Signature Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("245"),
        "grinds": FILTER_GRINDS,
        "stock": 130,
        "short_description": "Mild, sweet and forgiving — a big pot for a full table.",
        "short_description_ar": "معتدلة وحلوة ومتسامحة — إبريق كبير لمائدة كاملة.",
        "description": (
            "Built to survive being brewed by someone who has not had coffee yet. "
            "Low acidity, sweet finish, and it does not turn harsh as it cools."
        ),
        "description_ar": (
            "مصممة لتصمد أمام من يحضّرها قبل أن يشرب قهوته. حموضة منخفضة ونهاية "
            "حلوة، ولا تصبح حادة حين تبرد."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Peru / Colombia",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Caramel, cocoa, baked apple",
            "tasting_notes_ar": "كراميل، كاكاو، تفاح مخبوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.5"),
        },
    },
    {
        "code": "BLD-RSV",
        "name": "Roaster's Reserve Blend",
        "name_ar": "خلطة المحمصة المحفوظة",
        "category": "Signature Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("420"),
        "grinds": (Grind.WHOLE_BEAN, Grind.FILTER),
        "stock": 30,
        "featured": True,
        "short_description": "Whatever the head roaster thinks is best this month.",
        "short_description_ar": "ما يراه رئيس المحمصة الأفضل هذا الشهر.",
        "description": (
            "The composition changes with what lands well. Currently a Panama Geisha "
            "and Kenya AA split, roasted light. The only constant is that it is the "
            "best thing in the building."
        ),
        "description_ar": (
            "يتغير تركيبها بحسب ما يصلنا. حالياً مناصفة بين جيشا بنما وكينيا AA، "
            "بتحميص فاتح. الثابت الوحيد أنها أفضل ما في المحمصة."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Rotating micro-lots",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Floral, stone fruit, cane sugar",
            "tasting_notes_ar": "زهور، فاكهة ذات نواة، سكر قصب",
            "harvest_year": 2025,
            "cupping_score": Decimal("89.5"),
        },
    },
    {
        "code": "BLD-3CN",
        "name": "Three Continents Blend",
        "name_ar": "خلطة القارات الثلاث",
        "category": "Signature Blends",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("290"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 70,
        "short_description": "Africa, the Americas and Asia in one cup.",
        "short_description_ar": "أفريقيا والأمريكتان وآسيا في فنجان واحد.",
        "description": (
            "Ethiopia for aromatics, Colombia for sweetness, Sumatra for weight. An "
            "old-fashioned blending idea that still works: each continent covers what "
            "the others lack."
        ),
        "description_ar": (
            "إثيوبيا للعطر، وكولومبيا للحلاوة، وسومطرة للثقل. فكرة خلط قديمة ما زالت "
            "ناجحة: كل قارة تغطي ما ينقص الأخريات."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Ethiopia / Colombia / Sumatra",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cocoa, citrus peel, cedar",
            "tasting_notes_ar": "كاكاو، قشر حمضيات، خشب أرز",
            "harvest_year": 2025,
            "cupping_score": Decimal("85.0"),
        },
    },
    {
        "code": "BLD-COC",
        "name": "Dark Cocoa Blend",
        "name_ar": "خلطة الكاكاو الداكن",
        "category": "Signature Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("260"),
        "grinds": (Grind.WHOLE_BEAN, Grind.ESPRESSO, Grind.FRENCH_PRESS),
        "stock": 100,
        "short_description": "Unapologetically dark — bitter chocolate and roasted nut.",
        "short_description_ar": "داكنة بلا اعتذار — شوكولاتة مرة ومكسرات محمصة.",
        "description": (
            "For people who grew up on dark coffee and are not looking to be talked "
            "out of it. Roasted past second crack, heavy, and excellent with a lot of "
            "hot milk."
        ),
        "description_ar": (
            "لمن نشأ على القهوة الداكنة ولا ينوي التراجع عنها. محمصة بعد الطقطقة "
            "الثانية، ثقيلة، وممتازة مع كثير من الحليب الساخن."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / India",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Bitter chocolate, roasted nut, smoke",
            "tasting_notes_ar": "شوكولاتة مرة، مكسرات محمصة، دخان",
            "harvest_year": 2025,
            "cupping_score": Decimal("81.5"),
        },
    },
    {
        "code": "BLD-VLV",
        "name": "Velvet Crema Blend",
        "name_ar": "خلطة الكريما المخملية",
        "category": "Signature Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("300"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 85,
        "short_description": "Blended for crema — thick, sweet and slow to fade.",
        "short_description_ar": "مخلوطة من أجل الكريما — كثيفة وحلوة وبطيئة الذوبان.",
        "description": (
            "Fifteen percent washed robusta from India, which is what actually builds "
            "a lasting crema. The rest is Brazilian arabica for sweetness. Purists "
            "object; the cup wins."
        ),
        "description_ar": (
            "خمسة عشر بالمئة روبوستا مغسولة من الهند، وهي ما يبني الكريما الثابتة "
            "فعلاً. والباقي أرابيكا برازيلية للحلاوة. المتشددون يعترضون؛ والفنجان يكسب."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / India",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Toffee, hazelnut, black pepper",
            "tasting_notes_ar": "توفي، بندق، فلفل أسود",
            "harvest_year": 2025,
            "cupping_score": Decimal("82.0"),
        },
    },
    {
        "code": "BLD-PEA",
        "name": "Mountain Peak Blend",
        "name_ar": "خلطة قمة الجبل",
        "category": "Signature Blends",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("335"),
        "grinds": FILTER_GRINDS,
        "stock": 48,
        "short_description": "High-altitude lots only — dense, sweet and complex.",
        "short_description_ar": "محاصيل المرتفعات فقط — كثيفة وحلوة ومركّبة.",
        "description": (
            "Every component grown above 1,800 metres, where cold nights slow the "
            "cherry and pack in sugar. More expensive to buy, and it shows in the "
            "finish."
        ),
        "description_ar": (
            "كل مكوناتها مزروعة فوق 1800 متر، حيث تُبطئ الليالي الباردة نضج الثمرة "
            "وتكثف سكرها. أغلى في الشراء، ويظهر ذلك في النهاية."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Ethiopia / Colombia / Costa Rica",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Stone fruit, brown sugar, cocoa",
            "tasting_notes_ar": "فاكهة ذات نواة، سكر بني، كاكاو",
            "harvest_year": 2025,
            "cupping_score": Decimal("87.0"),
        },
    },

    # --- Espresso Blends -----------------------------------------------------
    {
        "code": "ESP-CLS",
        "name": "Jory Espresso Classico",
        "name_ar": "جوري إسبريسو كلاسيكو",
        "category": "Espresso Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("275"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 180,
        "featured": True,
        "short_description": "Our bar standard — chocolate, caramel, no sharp edges.",
        "short_description_ar": "معيار مقهانا — شوكولاتة وكراميل بلا حواف حادة.",
        "description": (
            "The blend on our own machine. Forgiving of a wandering grind setting, "
            "sweet at 1:2 in 28 seconds, and it does not go sour if you pull it short."
        ),
        "description_ar": (
            "الخلطة التي على ماكينتنا. متسامحة مع إعدادات الطحن المتغيرة، حلوة بنسبة "
            "1:2 في 28 ثانية، ولا تصبح حامضة إن قصّرت الاستخلاص."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Colombia",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Milk chocolate, caramel, almond",
            "tasting_notes_ar": "شوكولاتة بالحليب، كراميل، لوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.0"),
        },
    },
    {
        "code": "ESP-RIS",
        "name": "Ristretto Intenso",
        "name_ar": "ريستريتو إنتنسو",
        "category": "Espresso Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("285"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 120,
        "short_description": "Short, dark and syrupy. Built for a 1:1.5 ristretto.",
        "short_description_ar": "قصير وداكن وكثيف. لريستريتو بنسبة 1:1.5.",
        "description": (
            "Roasted dark enough that a short pull still tastes finished. Thick "
            "mouthfeel, long bittersweet finish, and it holds its own under a lot of "
            "steamed milk."
        ),
        "description_ar": (
            "محمصة بما يكفي ليأتي الاستخلاص القصير مكتمل المذاق. قوام سميك ونهاية "
            "طويلة بين المر والحلو، وتصمد تحت كمية كبيرة من الحليب المبخر."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Sumatra / India",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Dark chocolate, molasses, walnut",
            "tasting_notes_ar": "شوكولاتة داكنة، دبس، جوز",
            "harvest_year": 2025,
            "cupping_score": Decimal("82.5"),
        },
    },
    {
        "code": "ESP-PRO",
        "name": "Barista Pro Espresso",
        "name_ar": "باريستا برو إسبريسو",
        "category": "Espresso Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("265"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 160,
        "short_description": "The wholesale blend — consistent bag after bag.",
        "short_description_ar": "خلطة الجملة — ثابتة من كيس لآخر.",
        "description": (
            "What we sell to cafés, at the same price we sell it to them. Blended for "
            "consistency across harvests rather than for a headline flavour, so your "
            "dial-in does not move every month."
        ),
        "description_ar": (
            "ما نبيعه للمقاهي، وبنفس السعر الذي نبيعه لهم به. مخلوطة لتثبت عبر "
            "المواسم لا لتبرز نكهة بعينها، فلا تتغير إعداداتك كل شهر."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Honduras",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cocoa, roasted almond, caramel",
            "tasting_notes_ar": "كاكاو، لوز محمص، كراميل",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.0"),
        },
    },
    {
        "code": "ESP-GLD",
        "name": "Crema Gold Espresso",
        "name_ar": "كريما جولد إسبريسو",
        "category": "Espresso Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("295"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 90,
        "sale": True,
        "short_description": "Thick golden crema and a sweet, nutty middle.",
        "short_description_ar": "كريما ذهبية كثيفة ووسط حلو بطعم المكسرات.",
        "description": (
            "Natural-process Brazils do most of the work here — they carry the oils "
            "that make crema hold. Sweet enough to drink black, heavy enough for a "
            "flat white."
        ),
        "description_ar": (
            "البن البرازيلي المعالج طبيعياً يقوم بمعظم العمل هنا — فهو يحمل الزيوت "
            "التي تثبّت الكريما. حلوة بما يكفي لتُشرب سادة، وثقيلة بما يكفي للفلات وايت."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Guatemala",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Hazelnut, toffee, orange peel",
            "tasting_notes_ar": "بندق، توفي، قشر برتقال",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.5"),
        },
    },
    {
        "code": "ESP-DOP",
        "name": "Doppio Dark Espresso",
        "name_ar": "دوبيو دارك إسبريسو",
        "category": "Espresso Blends",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("255"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 140,
        "short_description": "Italian-style dark roast, bitter-sweet and bold.",
        "short_description_ar": "تحميص داكن على الطريقة الإيطالية، بين المر والحلو.",
        "description": (
            "The southern Italian idea of espresso: dark, low-acid, a little smoky, "
            "and unmistakable through two sugars. Not subtle and not trying to be."
        ),
        "description_ar": (
            "الفكرة الإيطالية الجنوبية عن الإسبريسو: داكن وقليل الحموضة ومدخن قليلاً، "
            "وواضح رغم ملعقتي سكر. ليس رقيقاً ولا يحاول أن يكون."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Vietnam / India",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Dark cocoa, smoke, black pepper",
            "tasting_notes_ar": "كاكاو داكن، دخان، فلفل أسود",
            "harvest_year": 2025,
            "cupping_score": Decimal("80.5"),
        },
    },
    {
        "code": "ESP-MLK",
        "name": "Milk-Forward Espresso",
        "name_ar": "إسبريسو للحليب",
        "category": "Espresso Blends",
        "roaster": "Jory Roastery",
        "base_price": Decimal("270"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 130,
        "short_description": "Blended to cut through milk without turning bitter.",
        "short_description_ar": "مخلوطة لتظهر عبر الحليب دون أن تصبح مرة.",
        "description": (
            "Most espresso disappears in a 12oz latte. This one does not: enough "
            "roast and enough body to still read as coffee under 300ml of milk, "
            "without the burnt edge that usually comes with it."
        ),
        "description_ar": (
            "معظم أنواع الإسبريسو تختفي في لاتيه كبير. هذه لا تختفي: تحميص وقوام "
            "يكفيان لتبقى قهوة تحت 300 مل من الحليب، بلا طعم الاحتراق المعتاد."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Colombia / India",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Chocolate malt, caramel, hazelnut",
            "tasting_notes_ar": "شعير بالشوكولاتة، كراميل، بندق",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.5"),
        },
    },
    {
        "code": "ESP-SOB",
        "name": "Single Origin Espresso — Brazil",
        "name_ar": "إسبريسو أصل واحد — البرازيل",
        "category": "Espresso Blends",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("280"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 75,
        "short_description": "One farm, one lot, dialled for the bar.",
        "short_description_ar": "مزرعة واحدة ومحصول واحد، معدّة لماكينة الإسبريسو.",
        "description": (
            "A single Mogiana lot roasted specifically for pressure rather than "
            "filter. Cleaner than a blend and more interesting, at the cost of "
            "needing a slightly tighter dial-in."
        ),
        "description_ar": (
            "محصول واحد من موجيانا، محمص خصيصاً للضغط لا للفلتر. أنظف من الخلطة "
            "وأكثر إثارة، مقابل إعداد أدق قليلاً."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Mogiana, São Paulo",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Peanut brittle, cocoa, red grape",
            "tasting_notes_ar": "حلوى الفول السوداني، كاكاو، عنب أحمر",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.0"),
        },
    },
    {
        "code": "ESP-NRD",
        "name": "Nordic Light Espresso",
        "name_ar": "إسبريسو نورديك فاتح",
        "category": "Espresso Blends",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("320"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 40,
        "short_description": "Light-roast espresso — acidic, fruity, needs a good grinder.",
        "short_description_ar": "إسبريسو فاتح التحميص — حمضي وفاكهي، يحتاج مطحنة جيدة.",
        "description": (
            "Roasted the way Oslo does it: light, fruit-driven and demanding. It will "
            "expose a cheap grinder and reward a good one. Not the blend for a "
            "high-volume bar."
        ),
        "description_ar": (
            "محمصة على طريقة أوسلو: فاتحة وفاكهية ومتطلبة. ستكشف المطحنة الرخيصة "
            "وتكافئ الجيدة. ليست خلطة لمقهى كثيف الحركة."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Ethiopia / Kenya",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Redcurrant, lime, floral",
            "tasting_notes_ar": "كشمش أحمر، ليمون أخضر، زهور",
            "harvest_year": 2025,
            "cupping_score": Decimal("87.5"),
        },
    },

    # --- Flavored Coffee -----------------------------------------------------
    {
        "code": "FLV-VAN",
        "name": "Vanilla Bean Coffee",
        "name_ar": "قهوة بالفانيليا",
        "category": "Flavored Coffee",
        "roaster": "Jory Roastery",
        "base_price": Decimal("265"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 100,
        "flavor": "Vanilla",
        "short_description": "Real Madagascar vanilla, added after the roast.",
        "short_description_ar": "فانيليا مدغشقر حقيقية، تُضاف بعد التحميص.",
        "description": (
            "Flavoured with actual vanilla extract on cooled beans, not sprayed on "
            "hot. Sweet and rounded without the chemical edge that gives flavoured "
            "coffee a bad name."
        ),
        "description_ar": (
            "تُنكّه بخلاصة فانيليا حقيقية على حبوب باردة، لا بالرش وهي ساخنة. حلوة "
            "ومستديرة بلا الطعم الكيميائي الذي أساء لسمعة القهوة المنكهة."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Vanilla, cream, milk chocolate",
            "tasting_notes_ar": "فانيليا، كريمة، شوكولاتة بالحليب",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-HAZ",
        "name": "Hazelnut Roast",
        "name_ar": "قهوة بالبندق",
        "category": "Flavored Coffee",
        "roaster": "Jory Roastery",
        "base_price": Decimal("265"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 110,
        "flavor": "Hazelnut",
        "featured": True,
        "short_description": "The best-selling flavour, and not by a small margin.",
        "short_description_ar": "النكهة الأكثر مبيعاً، وبفارق كبير.",
        "description": (
            "Roasted hazelnut over a Brazilian base that already tastes of nuts, so "
            "the flavour sits on top of the coffee rather than covering it."
        ),
        "description_ar": (
            "بندق محمص فوق قاعدة برازيلية طعمها أصلاً كالمكسرات، فتجلس النكهة فوق "
            "القهوة بدل أن تخفيها."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Hazelnut, praline, cocoa",
            "tasting_notes_ar": "بندق، برالين، كاكاو",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-CRM",
        "name": "Salted Caramel Coffee",
        "name_ar": "قهوة بالكراميل المملح",
        "category": "Flavored Coffee",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("270"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 95,
        "flavor": "Salted Caramel",
        "short_description": "Sweet, buttery and just salty enough to stay interesting.",
        "short_description_ar": "حلوة وزبدية ومالحة بما يكفي لتظل مثيرة.",
        "description": (
            "The salt is the point — it keeps the caramel from going cloying by the "
            "third sip. Very good iced, which is how most of it leaves the shop."
        ),
        "description_ar": (
            "الملح هو الفكرة — يمنع الكراميل من أن يصبح مُقززاً عند الرشفة الثالثة. "
            "ممتازة مثلجة، وهكذا يخرج معظمها من المحل."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Mogiana",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Caramel, butter, sea salt",
            "tasting_notes_ar": "كراميل، زبدة، ملح بحري",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-CHC",
        "name": "Chocolate Fudge Coffee",
        "name_ar": "قهوة بالشوكولاتة",
        "category": "Flavored Coffee",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("265"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 105,
        "flavor": "Chocolate",
        "short_description": "Dark chocolate fudge over a dark roast base.",
        "short_description_ar": "فدج الشوكولاتة الداكنة فوق قاعدة تحميص داكن.",
        "description": (
            "Doubling down: cocoa flavour on beans roasted dark enough to taste of "
            "cocoa already. Rich rather than sweet, and it makes a very good mocha."
        ),
        "description_ar": (
            "مضاعفة للتأثير: نكهة كاكاو على حبوب محمصة داكنة يفوح منها الكاكاو أصلاً. "
            "غنية أكثر منها حلوة، وتصنع موكا ممتازة."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Dark chocolate, fudge, malt",
            "tasting_notes_ar": "شوكولاتة داكنة، فدج، شعير",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-CIN",
        "name": "Cinnamon Spice Coffee",
        "name_ar": "قهوة بالقرفة",
        "category": "Flavored Coffee",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("260"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 85,
        "flavor": "Cinnamon",
        "short_description": "Ceylon cinnamon with a little clove and nutmeg.",
        "short_description_ar": "قرفة سيلانية مع قليل من القرنفل وجوزة الطيب.",
        "description": (
            "Warm rather than sharp — Ceylon cinnamon is softer than cassia. Sells "
            "out every Ramadan, so we now keep it year-round."
        ),
        "description_ar": (
            "دافئة لا حادة — القرفة السيلانية ألين من الصينية. تنفد كل رمضان، ولهذا "
            "صرنا نوفرها طوال العام."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Nariño",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cinnamon, clove, brown sugar",
            "tasting_notes_ar": "قرفة، قرنفل، سكر بني",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-CAR",
        "name": "Cardamom Coffee",
        "name_ar": "قهوة بالهيل",
        "category": "Flavored Coffee",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("280"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 120,
        "flavor": "Cardamom",
        "featured": True,
        "short_description": "Green cardamom ground in with the beans, the way it is done.",
        "short_description_ar": "هيل أخضر يُطحن مع البن، كما ينبغي.",
        "description": (
            "Whole green cardamom pods milled with the coffee rather than an extract "
            "added afterwards. Works as an espresso and works even better in a dallah."
        ),
        "description_ar": (
            "حبات هيل أخضر كاملة تُطحن مع البن بدل إضافة خلاصة بعد التحميص. تصلح "
            "إسبريسو، وتصلح في الدلة أكثر."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Sidamo",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cardamom, citrus, honey",
            "tasting_notes_ar": "هيل، حمضيات، عسل",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-COC",
        "name": "Coconut Cream Coffee",
        "name_ar": "قهوة بكريمة جوز الهند",
        "category": "Flavored Coffee",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("265"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 70,
        "flavor": "Coconut",
        "short_description": "Toasted coconut and cream. Outstanding over ice.",
        "short_description_ar": "جوز هند محمص وكريمة. رائعة على الثلج.",
        "description": (
            "Toasted rather than raw coconut, which keeps it from tasting like "
            "sunscreen. Built for cold brew — we cold-steep this one at the shop all "
            "summer."
        ),
        "description_ar": (
            "جوز هند محمص لا نيء، وهذا ما يمنعها من أن تشبه واقي الشمس. مصممة "
            "للتحضير البارد — ننقعها بارداً في المحل طوال الصيف."
        ),
        "profile": {
            "origin": "Peru",
            "region": "Cajamarca",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Toasted coconut, cream, vanilla",
            "tasting_notes_ar": "جوز هند محمص، كريمة، فانيليا",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-IRC",
        "name": "Irish Cream Coffee",
        "name_ar": "قهوة آيرش كريم",
        "category": "Flavored Coffee",
        "roaster": "Jory Roastery",
        "base_price": Decimal("275"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 60,
        "flavor": "Irish Cream",
        "short_description": "Cream, cocoa and a little whiskey character. Alcohol-free.",
        "short_description_ar": "كريمة وكاكاو ولمسة ويسكي. خالية من الكحول.",
        "description": (
            "The flavour profile of Irish cream without any alcohol in it — the "
            "whiskey note comes from vanilla and oak flavouring. Rich, and it wants "
            "no sugar."
        ),
        "description_ar": (
            "نكهة الآيرش كريم بلا أي كحول — طابع الويسكي يأتي من نكهتي الفانيليا "
            "وخشب البلوط. غنية، ولا تحتاج سكراً."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cream, cocoa, oak",
            "tasting_notes_ar": "كريمة، كاكاو، بلوط",
            "harvest_year": 2025,
        },
    },
    {
        "code": "FLV-MNT",
        "name": "Mocha Mint Coffee",
        "name_ar": "قهوة موكا بالنعناع",
        "category": "Flavored Coffee",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("270"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 55,
        "flavor": "Mint",
        "short_description": "Chocolate and mint — divisive, and its fans are loyal.",
        "short_description_ar": "شوكولاتة ونعناع — مثيرة للجدل، ومحبوها أوفياء.",
        "description": (
            "Nobody is neutral about this one. Cool mint over a dark cocoa base, best "
            "iced with a little milk, and it has a small following that buys nothing "
            "else."
        ),
        "description_ar": (
            "لا أحد محايد تجاهها. نعناع بارد فوق قاعدة كاكاو داكن، أفضل ما تكون مثلجة "
            "مع قليل من الحليب، ولها جمهور صغير لا يشتري غيرها."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Mogiana",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Mint, dark chocolate, cream",
            "tasting_notes_ar": "نعناع، شوكولاتة داكنة، كريمة",
            "harvest_year": 2025,
        },
    },

    # --- Turkish & Arabic ----------------------------------------------------
    {
        "code": "TRK-CLS",
        "name": "Turkish Coffee Classic",
        "name_ar": "قهوة تركي كلاسيك",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("210"),
        "grinds": TURKISH_GRINDS,
        "stock": 200,
        "featured": True,
        "short_description": "Milled to powder for the cezve. Dark, thick and traditional.",
        "short_description_ar": "مطحونة كالبودرة للكنكة. داكنة وثقيلة وتقليدية.",
        "description": (
            "Ground finer than espresso — closer to flour — because Turkish coffee is "
            "boiled, not filtered. Dark roasted so it holds up to sugar and a second "
            "boil."
        ),
        "description_ar": (
            "مطحونة أنعم من الإسبريسو — أقرب إلى الدقيق — لأن القهوة التركية تُغلى "
            "ولا تُصفى. تحميص داكن لتصمد أمام السكر والغلية الثانية."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Dark cocoa, walnut, brown sugar",
            "tasting_notes_ar": "كاكاو داكن، جوز، سكر بني",
            "harvest_year": 2025,
        },
    },
    {
        "code": "TRK-CAR",
        "name": "Turkish Coffee with Cardamom",
        "name_ar": "قهوة تركي بالهيل",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("230"),
        "grinds": TURKISH_GRINDS,
        "stock": 180,
        "flavor": "Cardamom",
        "featured": True,
        "short_description": "Classic Turkish with green cardamom milled in.",
        "short_description_ar": "تركي كلاسيك مع هيل أخضر مطحون معه.",
        "description": (
            "The default order in most of Egypt. Cardamom pods go through the mill "
            "with the beans, so every spoonful is spiced evenly rather than by luck."
        ),
        "description_ar": (
            "الطلب الافتراضي في معظم مصر. تمر حبات الهيل في المطحنة مع البن، فتتوزع "
            "التوابل بالتساوي في كل ملعقة لا بالصدفة."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Cardamom, dark cocoa, clove",
            "tasting_notes_ar": "هيل، كاكاو داكن، قرنفل",
            "harvest_year": 2025,
        },
    },
    {
        "code": "TRK-XDK",
        "name": "Turkish Coffee Extra Dark",
        "name_ar": "قهوة تركي غامقة جداً",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("215"),
        "grinds": TURKISH_GRINDS,
        "stock": 140,
        "short_description": "Roasted past the classic — bitter, smoky, uncompromising.",
        "short_description_ar": "محمصة أبعد من الكلاسيك — مرة ومدخنة وبلا مساومة.",
        "description": (
            "For the sada drinker who thinks the classic is too polite. Roasted well "
            "past second crack; take it without sugar or not at all."
        ),
        "description_ar": (
            "لشارب السادة الذي يرى الكلاسيك مهذبة أكثر من اللازم. محمصة بعد الطقطقة "
            "الثانية بكثير؛ اشربها بلا سكر أو لا تشربها."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Mogiana",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Bitter cocoa, smoke, charred nut",
            "tasting_notes_ar": "كاكاو مر، دخان، مكسرات محروقة",
            "harvest_year": 2025,
        },
    },
    {
        "code": "ARB-SAU",
        "name": "Saudi Arabic Coffee (Qahwa)",
        "name_ar": "قهوة عربية سعودية",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("280"),
        "grinds": (Grind.TURKISH, Grind.FILTER, Grind.WHOLE_BEAN),
        "stock": 90,
        "flavor": "Cardamom",
        "short_description": "Very light roast with cardamom — pale gold in the cup.",
        "short_description_ar": "تحميص فاتح جداً مع الهيل — ذهبية شاحبة في الفنجان.",
        "description": (
            "Gulf qahwa is barely roasted at all, which is why it pours light gold "
            "rather than black. Brewed long in a dallah with cardamom, and served in "
            "finjan without sugar alongside dates."
        ),
        "description_ar": (
            "القهوة الخليجية تكاد لا تُحمص، ولهذا تُسكب ذهبية فاتحة لا سوداء. تُغلى "
            "طويلاً في الدلة مع الهيل، وتُقدم في الفنجان بلا سكر مع التمر."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Harrar",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Cardamom, hay, citrus zest",
            "tasting_notes_ar": "هيل، قش، قشر حمضيات",
            "harvest_year": 2025,
        },
    },
    {
        "code": "ARB-EGY",
        "name": "Egyptian Ahwa Mazbout",
        "name_ar": "قهوة مصرية مظبوط",
        "category": "Turkish & Arabic",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("195"),
        "grinds": TURKISH_GRINDS,
        "stock": 250,
        "short_description": "The ahwa baladi grind, blended for a medium-sweet cup.",
        "short_description_ar": "طحنة القهوة البلدي، مخلوطة لفنجان مظبوط.",
        "description": (
            "What a Cairo ahwa actually serves. Balanced for one spoon of sugar per "
            "cup — mazbout — and priced so you can drink it all day, which is the "
            "point."
        ),
        "description_ar": (
            "ما تقدمه القهاوي في القاهرة فعلاً. متوازنة مع ملعقة سكر للفنجان — مظبوط "
            "— وبسعر يسمح بشربها طوال اليوم، وهذا هو المقصود."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Cerrado Mineiro",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cocoa, roasted grain, caramel",
            "tasting_notes_ar": "كاكاو، حبوب محمصة، كراميل",
            "harvest_year": 2025,
        },
    },
    {
        "code": "ARB-EMR",
        "name": "Emirati Gahwa Blend",
        "name_ar": "خلطة قهوة إماراتية",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("290"),
        "grinds": (Grind.TURKISH, Grind.FILTER),
        "stock": 60,
        "flavor": "Saffron",
        "short_description": "Light roast with saffron, cardamom and clove.",
        "short_description_ar": "تحميص فاتح مع الزعفران والهيل والقرنفل.",
        "description": (
            "The Emirati version leans on saffron alongside the cardamom, which "
            "gives it a deeper colour and a honeyed edge. Traditionally poured from "
            "a height, three-quarters short of the rim."
        ),
        "description_ar": (
            "النسخة الإماراتية تعتمد على الزعفران إلى جانب الهيل، فيمنحها لوناً أعمق "
            "وحافة عسلية. تُسكب تقليدياً من ارتفاع، وربع الفنجان فقط."
        ),
        "profile": {
            "origin": "Yemen",
            "region": "Haraz",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Saffron, cardamom, honey",
            "tasting_notes_ar": "زعفران، هيل، عسل",
            "harvest_year": 2025,
        },
    },
    {
        "code": "ARB-SAF",
        "name": "Arabic Coffee with Saffron",
        "name_ar": "قهوة عربية بالزعفران",
        "category": "Turkish & Arabic",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("340"),
        "grinds": (Grind.TURKISH, Grind.FILTER),
        "stock": 35,
        "flavor": "Saffron",
        "sale": True,
        "short_description": "Real saffron threads, not colouring. A special-occasion pot.",
        "short_description_ar": "خيوط زعفران حقيقية لا ملوّنات. لدلة المناسبات.",
        "description": (
            "Saffron is the reason for the price — we use whole Iranian threads, not "
            "the powder that is mostly safflower. Reserve this one for guests."
        ),
        "description_ar": (
            "الزعفران هو سبب السعر — نستخدم خيوطاً إيرانية كاملة، لا المسحوق الذي "
            "معظمه عصفر. احتفظ بها للضيوف."
        ),
        "profile": {
            "origin": "Yemen",
            "region": "Bani Matar",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Saffron, rosewater, honey",
            "tasting_notes_ar": "زعفران، ماء ورد، عسل",
            "harvest_year": 2025,
        },
    },

    # --- Decaf ---------------------------------------------------------------
    {
        "code": "DEC-COL",
        "name": "Decaf Colombia Swiss Water",
        "name_ar": "كولومبيا منزوعة الكافيين",
        "category": "Decaf",
        "roaster": "Jory Roastery",
        "base_price": Decimal("330"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 70,
        "featured": True,
        "short_description": "99.9% caffeine-free, decaffeinated with water only.",
        "short_description_ar": "خالية من الكافيين بنسبة 99.9%، منزوعة بالماء فقط.",
        "description": (
            "The Swiss Water process uses nothing but water, temperature and a carbon "
            "filter — no solvents. It costs more than chemical decaffeination and it "
            "is the reason this still tastes like Colombian coffee."
        ),
        "description_ar": (
            "طريقة الماء السويسري لا تستخدم سوى الماء والحرارة وفلتر كربوني — بلا "
            "مذيبات. تكلف أكثر من النزع الكيميائي، وهي سبب بقاء طعم البن الكولومبي."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Caramel, cocoa, red apple",
            "tasting_notes_ar": "كراميل، كاكاو، تفاح أحمر",
            "harvest_year": 2025,
            "cupping_score": Decimal("83.0"),
        },
    },
    {
        "code": "DEC-HSE",
        "name": "Decaf House Blend",
        "name_ar": "خلطة البيت منزوعة الكافيين",
        "category": "Decaf",
        "roaster": "Jory Roastery",
        "base_price": Decimal("310"),
        "grinds": ALL_ROUND_GRINDS,
        "stock": 85,
        "short_description": "The House Blend, minus the caffeine.",
        "short_description_ar": "الخلطة الأساسية، بلا كافيين.",
        "description": (
            "Same three-origin recipe as the House Blend, built from decaffeinated "
            "lots. For the second pot of the evening."
        ),
        "description_ar": (
            "نفس وصفة الأصول الثلاثة في الخلطة الأساسية، لكن من محاصيل منزوعة "
            "الكافيين. للإبريق الثاني في المساء."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Colombia / Ethiopia",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Milk chocolate, almond, apple",
            "tasting_notes_ar": "شوكولاتة بالحليب، لوز، تفاح",
            "harvest_year": 2025,
            "cupping_score": Decimal("82.0"),
        },
    },
    {
        "code": "DEC-ETH",
        "name": "Decaf Ethiopia",
        "name_ar": "إثيوبيا منزوعة الكافيين",
        "category": "Decaf",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("345"),
        "grinds": FILTER_GRINDS,
        "stock": 40,
        "short_description": "Sugarcane-process decaf that keeps the florals.",
        "short_description_ar": "منزوعة بقصب السكر مع بقاء الطابع الزهري.",
        "description": (
            "Decaffeinated with ethyl acetate derived from sugarcane, which is gentler "
            "on the aromatics than water alone. The jasmine survives, which almost "
            "never happens in a decaf."
        ),
        "description_ar": (
            "منزوعة الكافيين بأسيتات الإيثيل المستخلصة من قصب السكر، وهي أرفق "
            "بالعطريات من الماء وحده. الياسمين يبقى، وهذا نادر جداً في منزوعة الكافيين."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Sidamo",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Jasmine, lemon, honey",
            "tasting_notes_ar": "ياسمين، ليمون، عسل",
            "harvest_year": 2025,
            "cupping_score": Decimal("84.5"),
        },
    },
    {
        "code": "DEC-ESP",
        "name": "Decaf Espresso",
        "name_ar": "إسبريسو منزوع الكافيين",
        "category": "Decaf",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("320"),
        "grinds": ESPRESSO_GRINDS,
        "stock": 65,
        "short_description": "A decaf that actually pulls a proper shot.",
        "short_description_ar": "منزوعة كافيين تعطي استخلاصاً حقيقياً.",
        "description": (
            "Decaf beans are more brittle and take heat faster, so this is roasted on "
            "a separate profile. Thick crema, sweet finish, and nobody at the table "
            "can tell."
        ),
        "description_ar": (
            "حبوب منزوعة الكافيين أهش وتستقبل الحرارة أسرع، لذا تُحمص بمنحنى منفصل. "
            "كريما كثيفة ونهاية حلوة، ولا أحد على الطاولة يفرّق."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Colombia",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cocoa, toffee, hazelnut",
            "tasting_notes_ar": "كاكاو، توفي، بندق",
            "harvest_year": 2025,
            "cupping_score": Decimal("82.5"),
        },
    },
    {
        "code": "DEC-TRK",
        "name": "Decaf Turkish Grind",
        "name_ar": "تركي منزوع الكافيين",
        "category": "Decaf",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("300"),
        "grinds": TURKISH_GRINDS,
        "stock": 50,
        "short_description": "Powder-fine and caffeine-free, for a late cezve.",
        "short_description_ar": "ناعمة كالبودرة وبلا كافيين، لكنكة متأخرة.",
        "description": (
            "Turkish coffee is normally the last thing you can drink at night. This "
            "is the exception — same dark roast, same fine mill, no caffeine."
        ),
        "description_ar": (
            "القهوة التركية عادة آخر ما يمكن شربه ليلاً. هذه هي الاستثناء — نفس "
            "التحميص الداكن ونفس الطحن الناعم، بلا كافيين."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "roast_level": RoastLevel.DARK,
            "tasting_notes": "Dark cocoa, walnut, molasses",
            "tasting_notes_ar": "كاكاو داكن، جوز، دبس",
            "harvest_year": 2025,
            "cupping_score": Decimal("81.5"),
        },
    },

    # --- Green Beans ---------------------------------------------------------
    {
        "code": "GRN-BRA",
        "name": "Green Beans — Brazil Santos",
        "name_ar": "بن أخضر — برازيل سانتوس",
        "category": "Green Beans",
        "roaster": "Jory Roastery",
        "base_price": Decimal("420"),
        "grinds": NO_GRIND,
        "sizes": GREEN_SIZES,
        "stock": 300,
        "short_description": "Unroasted screen 17/18. The forgiving one to learn on.",
        "short_description_ar": "غير محمص مقاس 17/18. الأنسب لتتعلم عليه.",
        "description": (
            "Start here. Santos is even-sized, low in defects and wide open on "
            "roast profile — you can take it anywhere from City to Vienna and it "
            "will still be drinkable. Stored under 60% humidity."
        ),
        "description_ar": (
            "ابدأ من هنا. سانتوس متساوي الحجم وقليل العيوب ومرن في التحميص — يمكنك "
            "أخذه من التحميص الفاتح إلى الفييني وسيظل صالحاً للشرب. يُخزن تحت رطوبة 60%."
        ),
        "profile": {
            "origin": "Brazil",
            "region": "Santos, São Paulo",
            "process": Process.NATURAL,
            "altitude_masl": 1000,
            "tasting_notes": "Nutty, low acid, chocolate potential",
            "tasting_notes_ar": "مكسرات، حموضة منخفضة، إمكانية شوكولاتة",
            "harvest_year": 2025,
        },
    },
    {
        "code": "GRN-ETH",
        "name": "Green Beans — Ethiopia Djimma",
        "name_ar": "بن أخضر — إثيوبيا جيما",
        "category": "Green Beans",
        "roaster": "Nile Coffee Co.",
        "base_price": Decimal("480"),
        "grinds": NO_GRIND,
        "sizes": GREEN_SIZES,
        "stock": 180,
        "short_description": "Unroasted natural Djimma — fruit-forward, rewards a light roast.",
        "short_description_ar": "جيما طبيعي غير محمص — فاكهي، يكافئ التحميص الفاتح.",
        "description": (
            "Irregular bean size, so watch your drum charge — Djimma will scorch if "
            "you go in too hot. Take it to first crack and stop; the fruit is all in "
            "the light end."
        ),
        "description_ar": (
            "حجم الحبة غير منتظم، فانتبه لدرجة حرارة الشحن — جيما يحترق إن بدأت "
            "بحرارة عالية. أوصله إلى الطقطقة الأولى وتوقف؛ الفاكهة كلها في الطرف الفاتح."
        ),
        "profile": {
            "origin": "Ethiopia",
            "region": "Djimma, Oromia",
            "process": Process.NATURAL,
            "altitude_masl": 1800,
            "tasting_notes": "Berry, floral, bright acidity",
            "tasting_notes_ar": "توت، زهور، حموضة منعشة",
            "harvest_year": 2025,
        },
    },
    {
        "code": "GRN-COL",
        "name": "Green Beans — Colombia Excelso",
        "name_ar": "بن أخضر — كولومبيا إكسيلسو",
        "category": "Green Beans",
        "roaster": "Jory Roastery",
        "base_price": Decimal("450"),
        "grinds": NO_GRIND,
        "sizes": GREEN_SIZES,
        "stock": 220,
        "short_description": "Unroasted Excelso grade — dependable across every profile.",
        "short_description_ar": "درجة إكسيلسو غير محمصة — موثوقة في كل منحنيات التحميص.",
        "description": (
            "Excelso is the screen below Supremo and roasts more evenly for it. "
            "Good moisture content and a wide sweet spot — the green we keep in the "
            "most volume."
        ),
        "description_ar": (
            "إكسيلسو أصغر مقاساً من سوبريمو، ولهذا يتحمص بتساوٍ أكبر. نسبة رطوبة "
            "جيدة ومجال تحميص واسع — وهو البن الأخضر الأكثر توفراً لدينا."
        ),
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "altitude_masl": 1700,
            "tasting_notes": "Caramel, citrus, balanced",
            "tasting_notes_ar": "كراميل، حمضيات، متوازن",
            "harvest_year": 2025,
        },
    },
    {
        "code": "GRN-IND",
        "name": "Green Beans — India Cherry AB",
        "name_ar": "بن أخضر — الهند تشيري AB",
        "category": "Green Beans",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("380"),
        "grinds": NO_GRIND,
        "sizes": GREEN_SIZES,
        "stock": 260,
        "short_description": "Unroasted robusta for espresso blending and crema.",
        "short_description_ar": "روبوستا غير محمصة لخلطات الإسبريسو والكريما.",
        "description": (
            "Cherry AB is the grade most espresso blenders reach for when they want "
            "body and crema without paying arabica prices. Ten to twenty percent in "
            "a blend is usually enough."
        ),
        "description_ar": (
            "تشيري AB هي الدرجة التي يلجأ إليها خلّاطو الإسبريسو للحصول على القوام "
            "والكريما دون دفع سعر الأرابيكا. من عشرة إلى عشرين بالمئة في الخلطة تكفي عادة."
        ),
        "profile": {
            "origin": "India",
            "region": "Chikmagalur, Karnataka",
            "process": Process.NATURAL,
            "altitude_masl": 1100,
            "tasting_notes": "Woody, heavy body, high crema",
            "tasting_notes_ar": "خشبي، قوام ثقيل، كريما عالية",
            "harvest_year": 2025,
        },
    },
    {
        "code": "GRN-UGA",
        "name": "Green Beans — Uganda Robusta",
        "name_ar": "بن أخضر — روبوستا أوغندية",
        "category": "Green Beans",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("360"),
        "grinds": NO_GRIND,
        "sizes": GREEN_SIZES,
        "stock": 240,
        "short_description": "Unroasted washed robusta — cleaner than the Indian.",
        "short_description_ar": "روبوستا مغسولة غير محمصة — أنظف من الهندية.",
        "description": (
            "Uganda grows robusta natively rather than as a cash crop, and the washed "
            "lots are noticeably cleaner than the standard. Still robusta — expect "
            "weight, not delicacy."
        ),
        "description_ar": (
            "تنمو الروبوستا في أوغندا بشكل أصلي لا كمحصول نقدي، والمحاصيل المغسولة "
            "أنظف بوضوح من المعتاد. تبقى روبوستا — توقع الثقل لا الرقة."
        ),
        "profile": {
            "origin": "Uganda",
            "region": "Bugisu",
            "process": Process.WASHED,
            "altitude_masl": 1400,
            "tasting_notes": "Cedar, dark cocoa, heavy body",
            "tasting_notes_ar": "خشب أرز، كاكاو داكن، قوام ثقيل",
            "harvest_year": 2025,
        },
    },

    # --- Sampler & Gift Sets -------------------------------------------------
    {
        "code": "SET-DSC",
        "name": "Single Origin Discovery Set",
        "name_ar": "علبة اكتشاف الأصل الواحد",
        "category": "Sampler & Gift Sets",
        "roaster": "Jory Roastery",
        "base_price": Decimal("780"),
        "grinds": (Grind.WHOLE_BEAN, Grind.FILTER),
        "sizes": SET_SIZES,
        "stock": 45,
        "featured": True,
        "short_description": "Three 250g bags: Ethiopia, Kenya and Colombia.",
        "short_description_ar": "ثلاثة أكياس 250 جم: إثيوبيا وكينيا وكولومبيا.",
        "description": (
            "The three origins that teach you the most about your own palate, side "
            "by side. Floral, acidic and balanced — brew them within a week of each "
            "other and the differences stop being abstract."
        ),
        "description_ar": (
            "الأصول الثلاثة التي تعلمك أكثر ما يمكن عن ذوقك، جنباً إلى جنب. زهرية "
            "وحمضية ومتوازنة — حضّرها خلال أسبوع واحد وستتوقف الفروق عن كونها نظرية."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Ethiopia / Kenya / Colombia",
            "process": Process.WASHED,
            "roast_level": RoastLevel.LIGHT,
            "tasting_notes": "Floral, blackcurrant, caramel",
            "tasting_notes_ar": "زهور، كشمش أسود، كراميل",
            "harvest_year": 2025,
        },
    },
    {
        "code": "SET-GFT",
        "name": "Jory Signature Gift Box",
        "name_ar": "علبة جوري للهدايا",
        "category": "Sampler & Gift Sets",
        "roaster": "Jory Roastery",
        "base_price": Decimal("850"),
        "grinds": (Grind.WHOLE_BEAN, Grind.FILTER, Grind.ESPRESSO),
        "sizes": SET_SIZES,
        "stock": 40,
        "sale": True,
        "short_description": "Three signature blends in a presentation box, with a card.",
        "short_description_ar": "ثلاث خلطات مميزة في علبة تقديم، مع بطاقة.",
        "description": (
            "House, Morning and Nile Valley in 250g bags, boxed with a handwritten "
            "card. The safe gift for someone whose taste in coffee you do not know."
        ),
        "description_ar": (
            "الأساسية والصباح ووادي النيل في أكياس 250 جم، معبأة مع بطاقة مكتوبة "
            "بخط اليد. الهدية الآمنة لمن لا تعرف ذوقه في القهوة."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "House / Morning / Nile Valley",
            "process": Process.WASHED,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Chocolate, citrus, berries",
            "tasting_notes_ar": "شوكولاتة، حمضيات، توت",
            "harvest_year": 2025,
        },
    },
    {
        "code": "SET-TRK",
        "name": "Turkish & Arabic Tasting Set",
        "name_ar": "علبة تذوق التركي والعربي",
        "category": "Sampler & Gift Sets",
        "roaster": "Red Sea Roasters",
        "base_price": Decimal("690"),
        "grinds": (Grind.TURKISH,),
        "sizes": SET_SIZES,
        "stock": 35,
        "short_description": "Turkish classic, cardamom Turkish and Saudi qahwa.",
        "short_description_ar": "تركي كلاسيك، تركي بالهيل، وقهوة سعودية.",
        "description": (
            "Three regional traditions in one box — the dark Turkish, the spiced "
            "Turkish, and the pale Gulf qahwa that surprises everyone who has only "
            "had the first two."
        ),
        "description_ar": (
            "ثلاثة تقاليد إقليمية في علبة واحدة — التركي الداكن، والتركي بالهيل، "
            "والقهوة الخليجية الفاتحة التي تفاجئ كل من لم يجرب سوى الأولين."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Ethiopia",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cardamom, dark cocoa, citrus",
            "tasting_notes_ar": "هيل، كاكاو داكن، حمضيات",
            "harvest_year": 2025,
        },
    },
    {
        "code": "SET-ESP",
        "name": "Espresso Lovers Trio",
        "name_ar": "ثلاثية عشاق الإسبريسو",
        "category": "Sampler & Gift Sets",
        "roaster": "Cairo Bean Works",
        "base_price": Decimal("740"),
        "grinds": (Grind.WHOLE_BEAN, Grind.ESPRESSO),
        "sizes": SET_SIZES,
        "stock": 38,
        "short_description": "Classico, Ristretto Intenso and Nordic Light, 250g each.",
        "short_description_ar": "كلاسيكو وريستريتو إنتنسو ونورديك، 250 جم لكل منها.",
        "description": (
            "Light, medium and dark espresso side by side, so you can find where "
            "on that line your machine and your milk actually want to sit."
        ),
        "description_ar": (
            "إسبريسو فاتح ومتوسط وداكن جنباً إلى جنب، لتكتشف أين على هذا الخط "
            "تريد ماكينتك وحليبك أن يستقرا."
        ),
        "profile": {
            "origin": "Multi-Origin",
            "region": "Brazil / Ethiopia / Kenya",
            "process": Process.NATURAL,
            "roast_level": RoastLevel.MEDIUM,
            "tasting_notes": "Cocoa, redcurrant, molasses",
            "tasting_notes_ar": "كاكاو، كشمش أحمر، دبس",
            "harvest_year": 2025,
        },
    },
]


# --- Equipment and roasting machines -----------------------------------------
#
# A lighter branch: enough rows to exercise HardwareProfile, the brand filter
# and the machine-type facet. Variants are explicit here — hardware has no
# weight ladder to generate from.
# (sku suffix, label, label_ar, price, compare_at, stock)

HARDWARE = [
    {
        "code": "EQP-BAR-ENC",
        "name": "Baratza Encore Burr Grinder",
        "name_ar": "مطحنة باراتزا إنكور",
        "category": "Grinders",
        "type": ProductType.EQUIPMENT,
        "brand": "Baratza",
        "machine_type": MachineType.GRINDER,
        "short_description": "40 grind settings, conical burrs. The standard first grinder.",
        "short_description_ar": "40 درجة طحن بأقراص مخروطية. المطحنة الأولى المعيارية.",
        "description": (
            "The grinder most people should buy first. Consistent enough for pour-over "
            "and French press, serviceable with a screwdriver, and parts are still "
            "available a decade on."
        ),
        "description_ar": (
            "المطحنة التي يجدر بمعظم الناس شراؤها أولاً. ثباتها يكفي للتقطير اليدوي "
            "والفرنش برس، ويمكن صيانتها بمفك، وقطع غيارها متوفرة بعد عشر سنوات."
        ),
        "variants": [
            ("BLK", "Black", "أسود", Decimal("8900"), None, 12),
            ("WHT", "White", "أبيض", Decimal("8900"), None, 7),
        ],
    },
    {
        "code": "EQP-FEL-ODE",
        "name": "Fellow Ode Brew Grinder Gen 2",
        "name_ar": "مطحنة فيلو أودي الجيل الثاني",
        "category": "Grinders",
        "type": ProductType.EQUIPMENT,
        "brand": "Fellow",
        "machine_type": MachineType.GRINDER,
        "short_description": "64mm flat burrs, filter-only. Very low retention.",
        "short_description_ar": "أقراص مسطحة 64 مم، للفلتر فقط. احتباس منخفض جداً.",
        "description": (
            "Flat burrs give a tighter particle distribution than conical, which shows "
            "up as clarity in a filter brew. Deliberately not an espresso grinder — it "
            "does not go fine enough, by design."
        ),
        "description_ar": (
            "الأقراص المسطحة تعطي توزيعاً أدق للجزيئات من المخروطية، وهذا يظهر نقاءً "
            "في تحضير الفلتر. ليست مطحنة إسبريسو عمداً — لا تصل إلى النعومة الكافية."
        ),
        "variants": [
            ("MAT", "Matte Black", "أسود مطفي", Decimal("18500"), Decimal("21000"), 6),
        ],
    },
    {
        "code": "EQP-HAR-SKR",
        "name": "Hario Skerton Pro Hand Grinder",
        "name_ar": "مطحنة هاريو سكيرتون برو اليدوية",
        "category": "Grinders",
        "type": ProductType.EQUIPMENT,
        "brand": "Hario",
        "machine_type": MachineType.GRINDER,
        "short_description": "Ceramic burrs, no electricity. Travels well.",
        "short_description_ar": "أقراص سيراميك بلا كهرباء. مناسبة للسفر.",
        "description": (
            "Ceramic burrs do not rust and do not care about being packed in a bag. "
            "Slower than an electric grinder and quieter than an argument at 6am."
        ),
        "description_ar": (
            "أقراص السيراميك لا تصدأ ولا تتأثر بالحشر في حقيبة. أبطأ من المطحنة "
            "الكهربائية وأهدأ من نقاش في السادسة صباحاً."
        ),
        "variants": [
            ("STD", "Standard", "قياسي", Decimal("3200"), None, 25),
        ],
    },
    {
        "code": "EQP-CHM-6CP",
        "name": "Chemex Classic 6-Cup",
        "name_ar": "كيمكس كلاسيك 6 أكواب",
        "category": "Brewers & Drippers",
        "type": ProductType.EQUIPMENT,
        "brand": "Chemex",
        "machine_type": MachineType.BREWER,
        "short_description": "Borosilicate carafe with a wood collar. Thick filters, clean cup.",
        "short_description_ar": "دورق زجاجي بطوق خشبي. فلاتر سميكة وفنجان نظيف.",
        "description": (
            "The heavy bonded filters are the whole point — they strip the oils and "
            "leave a cup with almost no body and a lot of clarity. In the permanent "
            "collection at MoMA, and it still just makes coffee."
        ),
        "description_ar": (
            "الفلاتر السميكة هي الفكرة كلها — تحجز الزيوت وتترك فنجاناً بلا قوام تقريباً "
            "وبنقاء عالٍ. موجود في المجموعة الدائمة بمتحف MoMA، وما زال مجرد صانع قهوة."
        ),
        "variants": [
            ("6CP", "6-cup", "6 أكواب", Decimal("4200"), None, 18),
            ("8CP", "8-cup", "8 أكواب", Decimal("4900"), None, 10),
        ],
    },
    {
        "code": "EQP-HAR-V60",
        "name": "Hario V60 Ceramic Dripper 02",
        "name_ar": "هاريو V60 دريبر سيراميك 02",
        "category": "Brewers & Drippers",
        "type": ProductType.EQUIPMENT,
        "brand": "Hario",
        "machine_type": MachineType.BREWER,
        "short_description": "The 60-degree cone with the spiral ribs. Endlessly adjustable.",
        "short_description_ar": "مخروط بزاوية 60 درجة بأضلاع حلزونية. قابل للضبط بلا حدود.",
        "description": (
            "A single large hole and spiral ribs mean the water flow is yours to "
            "control — grind and pour rate change everything. Frustrating for a week, "
            "then the most flexible brewer you own."
        ),
        "description_ar": (
            "فتحة واحدة كبيرة وأضلاع حلزونية تعني أن تدفق الماء بيدك — الطحن وسرعة "
            "الصب يغيران كل شيء. محبط لأسبوع، ثم يصبح أكثر أدواتك مرونة."
        ),
        "variants": [
            ("WHT", "White", "أبيض", Decimal("1150"), None, 40),
            ("BLK", "Black", "أسود", Decimal("1250"), None, 30),
        ],
    },
    {
        "code": "EQP-HAR-SWT",
        "name": "Hario Switch Immersion Dripper",
        "name_ar": "هاريو سويتش للنقع والتقطير",
        "category": "Brewers & Drippers",
        "type": ProductType.EQUIPMENT,
        "brand": "Hario",
        "machine_type": MachineType.BREWER,
        "short_description": "V60 geometry with a valve — immersion and percolation in one.",
        "short_description_ar": "هندسة V60 مع صمام — نقع وترشيح في أداة واحدة.",
        "description": (
            "Close the valve and it is a steeper; open it and it drains like a V60. "
            "The hybrid brews are where it gets interesting — steep for two minutes, "
            "then release."
        ),
        "description_ar": (
            "أغلق الصمام فتصير أداة نقع، وافتحه فتصفّي كـ V60. التحضير الهجين هو "
            "الأمتع — انقع دقيقتين ثم افتح."
        ),
        "variants": [
            ("CLR", "Clear", "شفاف", Decimal("2400"), None, 22),
        ],
    },
    {
        "code": "EQP-FEL-EKG",
        "name": "Fellow Stagg EKG Electric Kettle",
        "name_ar": "غلاية فيلو ستاج EKG الكهربائية",
        "category": "Kettles",
        "type": ProductType.EQUIPMENT,
        "brand": "Fellow",
        "machine_type": MachineType.KETTLE,
        "short_description": "Gooseneck with 1°C control and a hold function.",
        "short_description_ar": "عنق إوزة مع تحكم بدرجة واحدة ووظيفة تثبيت الحرارة.",
        "description": (
            "Temperature to the degree and a counterbalanced handle that makes a slow "
            "pour possible. The hold function is what you actually end up using every "
            "morning."
        ),
        "description_ar": (
            "تحكم في الحرارة بالدرجة الواحدة ومقبض متوازن يتيح صباً بطيئاً. وظيفة "
            "تثبيت الحرارة هي ما ستستخدمه فعلاً كل صباح."
        ),
        "variants": [
            ("MAT", "Matte Black", "أسود مطفي", Decimal("14500"), Decimal("16500"), 9),
            ("SST", "Polished Steel", "ستانلس ملمّع", Decimal("15200"), None, 5),
        ],
    },
    {
        "code": "EQP-HAR-BNO",
        "name": "Hario Buono Stovetop Kettle",
        "name_ar": "غلاية هاريو بونو للموقد",
        "category": "Kettles",
        "type": ProductType.EQUIPMENT,
        "brand": "Hario",
        "machine_type": MachineType.KETTLE,
        "short_description": "Stainless gooseneck for gas or induction. No electronics.",
        "short_description_ar": "عنق إوزة ستانلس للغاز أو الحث. بلا إلكترونيات.",
        "description": (
            "The pour control of a gooseneck without paying for a thermostat. Use a "
            "thermometer, or boil and wait thirty seconds — that lands you around 93°C."
        ),
        "description_ar": (
            "تحكم في الصب كعنق الإوزة دون دفع ثمن الترموستات. استخدم مقياس حرارة، أو "
            "اغلِ الماء وانتظر ثلاثين ثانية — تصل بذلك إلى نحو 93 درجة."
        ),
        "variants": [
            ("1L", "1.0L", "1 لتر", Decimal("3600"), None, 20),
            ("12L", "1.2L", "1.2 لتر", Decimal("3900"), None, 14),
        ],
    },
    {
        "code": "EQP-HAR-SCL",
        "name": "Hario V60 Drip Scale",
        "name_ar": "ميزان هاريو V60 للتقطير",
        "category": "Accessories",
        "type": ProductType.EQUIPMENT,
        "brand": "Hario",
        "machine_type": MachineType.OTHER,
        "short_description": "0.1g resolution with a built-in timer.",
        "short_description_ar": "دقة 0.1 جم مع مؤقت مدمج.",
        "description": (
            "A scale with a timer is the single cheapest upgrade to your coffee. "
            "Weighing the dose and the water turns a good brew from an accident into "
            "something you can repeat."
        ),
        "description_ar": (
            "الميزان بمؤقت هو أرخص تحسين ممكن لقهوتك. وزن الجرعة والماء يحوّل الفنجان "
            "الجيد من صدفة إلى شيء يمكن تكراره."
        ),
        "variants": [
            ("STD", "Standard", "قياسي", Decimal("2800"), Decimal("3300"), 30),
        ],
    },
    {
        "code": "EQP-FEL-ATM",
        "name": "Fellow Atmos Vacuum Canister 1.2L",
        "name_ar": "علبة فيلو أتموس المفرغة 1.2 لتر",
        "category": "Accessories",
        "type": ProductType.EQUIPMENT,
        "brand": "Fellow",
        "machine_type": MachineType.OTHER,
        "short_description": "Twist the lid to pull a vacuum. Slows staling.",
        "short_description_ar": "أدر الغطاء لسحب الهواء. يبطئ تقادم البن.",
        "description": (
            "Oxygen is what stales coffee, so removing it buys you time — not "
            "forever, but a noticeable week or two. Holds a 1kg bag with room to "
            "spare."
        ),
        "description_ar": (
            "الأكسجين هو ما يُقدّم البن، وإزالته تكسبك وقتاً — ليس إلى الأبد، لكن "
            "أسبوعاً أو أسبوعين محسوسين. تتسع لكيس 1 كجم وأكثر."
        ),
        "variants": [
            ("SST", "Steel", "ستانلس", Decimal("3400"), None, 24),
            ("GLS", "Glass", "زجاج", Decimal("3100"), None, 16),
        ],
    },
    {
        "code": "RST-GSN-W1A",
        "name": "Giesen W1A Home Roaster",
        "name_ar": "محمصة جيزن W1A المنزلية",
        "category": "Home Roasters",
        "type": ProductType.ROASTING_MACHINE,
        "brand": "Giesen",
        "machine_type": MachineType.DRUM_ROASTER,
        "short_description": "1kg drum roaster with profile logging. Shop control at home.",
        "short_description_ar": "محمصة أسطوانية 1 كجم مع تسجيل المنحنيات. تحكم احترافي بالمنزل.",
        "description": (
            "A real drum roaster scaled down: separate control of drum speed, airflow "
            "and gas, with profile logging over USB. The step where home roasting "
            "stops being a hobby."
        ),
        "description_ar": (
            "محمصة أسطوانية حقيقية بحجم مصغر: تحكم منفصل في سرعة الأسطوانة وتدفق "
            "الهواء والغاز، مع تسجيل المنحنيات عبر USB. الخطوة التي يتوقف عندها "
            "التحميص المنزلي عن كونه هواية."
        ),
        "variants": [
            ("RED", "Racing Red", "أحمر", Decimal("385000"), None, 2),
            ("BLK", "Black", "أسود", Decimal("385000"), None, 1),
        ],
    },
    {
        "code": "RST-PRB-P12",
        "name": "Probat P12 Shop Roaster",
        "name_ar": "محمصة بروبات P12 التجارية",
        "category": "Shop Roasters",
        "type": ProductType.ROASTING_MACHINE,
        "brand": "Probat",
        "machine_type": MachineType.DRUM_ROASTER,
        "short_description": "12kg batches. The café roaster that outlives the café.",
        "short_description_ar": "دفعات 12 كجم. محمصة المقهى التي تعمّر أكثر منه.",
        "description": (
            "Cast-iron drum, mechanical simplicity and a parts supply measured in "
            "decades. Installation and a gas line are on you; we will do the first "
            "profile with you."
        ),
        "description_ar": (
            "أسطوانة حديد زهر وبساطة ميكانيكية وقطع غيار تُقاس بالعقود. التركيب "
            "وخط الغاز عليك؛ ونحن نضبط أول منحنى تحميص معك."
        ),
        "variants": [
            ("STD", "Standard", "قياسي", Decimal("1450000"), None, 1),
        ],
    },
    {
        "code": "RST-GSN-W6A",
        "name": "Giesen W6A Shop Roaster",
        "name_ar": "محمصة جيزن W6A التجارية",
        "category": "Shop Roasters",
        "type": ProductType.ROASTING_MACHINE,
        "brand": "Giesen",
        "machine_type": MachineType.DRUM_ROASTER,
        "short_description": "6kg batches with full software profiling.",
        "short_description_ar": "دفعات 6 كجم مع برنامج كامل لضبط المنحنيات.",
        "description": (
            "The size most small roasteries settle on: enough for wholesale, small "
            "enough to keep single-origin lots separate. Profiles save and replay, "
            "which is how you stay consistent when you are not the one roasting."
        ),
        "description_ar": (
            "الحجم الذي تستقر عليه معظم المحامص الصغيرة: يكفي للجملة، وصغير بما يكفي "
            "لفصل محاصيل الأصل الواحد. تُحفظ المنحنيات وتُعاد، وهكذا تحافظ على الثبات "
            "حين لا تكون أنت من يحمّص."
        ),
        "variants": [
            ("STD", "Standard", "قياسي", Decimal("890000"), None, 2),
        ],
    },
]
