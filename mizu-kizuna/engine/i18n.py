"""Textes du moteur en 3 langues : fr (français), tn (tunisien / derja), ja (japonais)."""
from contextvars import ContextVar

LANG = ContextVar("lang", default="fr")
LANGS = ("fr", "tn", "ja")

M = {
 # niveaux d'adéquation
 "lvl.tres": {"fr": "Très adapté", "tn": "ملايم برشا", "ja": "非常に適している"},
 "lvl.adapte": {"fr": "Adapté", "tn": "ملايم", "ja": "適している"},
 "lvl.possible": {"fr": "Possible avec précautions", "tn": "ممكن مع شويّة احتياط", "ja": "注意すれば可能"},
 "lvl.deconseille": {"fr": "Déconseillé", "tn": "ما ننصحوكش بيه", "ja": "おすすめしません"},
 # raisons (adéquation)
 "r.ph_out": {"fr": "pH du sol ({ph}) hors de l'optimum de la culture ({lo}–{hi})",
              "tn": "الـpH متاع الأرض ({ph}) موش في القياس الباهي للزرعة ({lo}–{hi})",
              "ja": "土壌pH（{ph}）が作物の最適範囲（{lo}～{hi}）から外れています"},
 "r.texture": {"fr": "texture {soil} peu adaptée (préfère : {pref})",
               "tn": "نوع الأرض ({soil}) موش مناسب برشا (تحبّ: {pref})",
               "ja": "土性（{soil}）があまり合いません（好む土性：{pref}）"},
 "r.salt": {"fr": "sensible au sel (seuil {thr} dS/m) : perte de rendement estimée {loss} %",
            "tn": "تخاف من الملح (الحدّ {thr} dS/m): الصابة تنقص بحوالي {loss}٪",
            "ja": "塩に弱い（許容値 {thr} dS/m）：収量が約{loss}%減る見込み"},
 "r.water_short": {"fr": "besoin d'une année sèche ({need} m³/ha) supérieur à votre eau ({avail} m³/ha)",
                   "tn": "في عام شايح تستحقّ {need} م³/هك، وإنتي عندك {avail} م³/هك برك",
                   "ja": "干ばつ年の必要水量（{need} m³/ha）が利用可能水量（{avail} m³/ha）を上回ります"},
 "r.needs_irrig": {"fr": "a besoin d'irrigation : ne se cultive pas en sec ici",
                   "tn": "تستحقّ السقي: ما تنجمش تتزرع بالمطر برك هوني",
                   "ja": "灌漑が必要：ここでは天水栽培できません"},
 "r.rain_low": {"fr": "pluie insuffisante en sec ({rain} mm/an en moyenne, il en faut au moins {opt} mm)",
                "tn": "المطر ما يكفيش بلاش سقي ({rain} مم في العام، تستحقّ على الأقل {opt} مم)",
                "ja": "天水栽培には雨が不足（年平均{rain} mm、最低{opt} mm必要）"},
 "r.frost": {"fr": "gel destructeur pendant la saison {pct} % des années",
             "tn": "الجليد يضرّها في {pct}٪ من السنين",
             "ja": "{pct}%の年で生育期間中に致命的な霜害"},
 "r.heat": {"fr": "canicule pendant la saison {pct} % des années",
            "tn": "السخانة الكبيرة تضرّها في {pct}٪ من السنين",
            "ja": "{pct}%の年で生育期間中に猛暑"},
 "r.temp_far": {"fr": "températures de saison éloignées de l'optimum de la culture",
                "tn": "السخانة والبرد في الموسم موش مناسبين للزرعة",
                "ja": "生育期の気温が作物の最適範囲から離れています"},
 "r.water_big": {"fr": "besoin en eau élevé : environ {need} m³/ha par an", "tn": "تستحقّ برشا ماء: حوالي {need} م³/هك في العام", "ja": "必要水量が多い：年間 約{need} m³/ha"},
 "r.heat_units": {"fr": "chaleur d'été pour mûrir les dattes : {hu} °C·j (il faut ≈ {req})", "tn": "سخانة الصيف باش تطيب الدقلة: {hu} درجة·يوم (تستحقّ ≈ {req})", "ja": "ナツメヤシの実の成熟に必要な夏の積算温度：{hu} °C·日（必要量 約{req}）"},
 "p.regional": {"fr": "spécialité de votre région : ce climat convient bien mieux à cette culture que la moyenne du pays", "tn": "اختصاص جهتك: الطقس هوني يناسب الزرعة هاذي برشا أكثر من بقية البلاد", "ja": "地域の特産：この気候は国内平均よりもこの作物にずっと適しています"},
 "p.traditional": {"fr": "culture traditionnelle de la région ({region})", "tn": "زرعة معروفة في الجهة ({region})", "ja": "この地域の伝統的な作物（{region}）"},
 "p.temp_good": {"fr": "températures favorables la plupart des années", "tn": "الطقس مناسب في أغلب السنين",
                 "ja": "ほとんどの年で気温が良好"},
 "p.no_risk": {"fr": "aucun gel ni canicule critique sur {n} ans", "tn": "لا جليد لا سخانة خطيرة في {n} عام",
               "ja": "{n}年間、致命的な霜害も猛暑もなし"},
 "p.soil_ok": {"fr": "sol compatible (pH et texture)", "tn": "الأرض مناسبة (الـpH ونوع التربة)", "ja": "土壌が適合（pHと土性）"},
 "p.nfix": {"fr": "enrichit le sol en azote", "tn": "تزيد الآزوت للأرض (تسمّدها)", "ja": "土壌に窒素を供給"},
 "tex.light": {"fr": "léger", "tn": "خفيفة (رملية)", "ja": "軽い土"},
 "tex.medium": {"fr": "moyen", "tn": "وسط", "ja": "中程度の土"},
 "tex.heavy": {"fr": "lourd", "tn": "ثقيلة (طينية)", "ja": "重い土"},
 "tex.organic": {"fr": "organique", "tn": "فيها برشا مادّة عضوية", "ja": "有機質土"},
 # sol
 "s.group.light": {"fr": "léger (sableux)", "tn": "خفيفة (رملية)", "ja": "軽い（砂質）"},
 "s.group.medium": {"fr": "moyen (limoneux)", "tn": "وسط (طميية)", "ja": "中程度（壌土）"},
 "s.group.heavy": {"fr": "lourd (argileux)", "tn": "ثقيلة (طينية)", "ja": "重い（粘土質）"},
 "s.a.alk": {"fr": "pH très alcalin ({ph}) : risque de carences (fer, zinc), sol souvent calcaire.",
             "tn": "الأرض كلسية برشا (pH {ph}): ينجم يصير نقص في الحديد والزنك.",
             "ja": "強アルカリ性（pH {ph}）：鉄・亜鉛欠乏の恐れ。石灰質土壌が多い。"},
 "s.a.acid": {"fr": "Sol acide (pH {ph}) : à corriger (chaulage) pour beaucoup de cultures.",
              "tn": "الأرض حامضة (pH {ph}): تستحقّ الجير لبرشا زرايع.",
              "ja": "酸性土壌（pH {ph}）：多くの作物で石灰による矯正が必要。"},
 "s.a.om": {"fr": "Matière organique faible ({soc} g/kg) : apports de fumier ou de compost recommandés.",
            "tn": "المادّة العضوية قليلة ({soc} غ/كغ): زيد الغبار ولا الكومبوست.",
            "ja": "有機物が少ない（{soc} g/kg）：堆肥の施用をおすすめします。"},
 "s.a.light": {"fr": "Sol léger : retient peu l'eau, préférer le goutte-à-goutte et des arrosages fréquents.",
               "tn": "أرض خفيفة: ما تشدّش الماء، الأحسن قطرة قطرة وسقي على مرّات.",
               "ja": "軽い土：保水力が低いので、点滴灌漑と少量多回数の灌水を。"},
 "s.a.heavy": {"fr": "Sol lourd : risque d'asphyxie si excès d'eau, éviter les cultures à tubercules sensibles.",
               "tn": "أرض ثقيلة: كان زاد الماء العروق تختنق، ابعد على الزرايع اللي تعمل درنات.",
               "ja": "重い土：過湿で根腐れの恐れ。イモ類は避けましょう。"},
 "s.src.user": {"fr": "indiqué par l'agriculteur", "tn": "الفلاّح هو اللي اختارها", "ja": "農家の申告"},
 "s.src.sg": {"fr": "SoilGrids 2.0 (ISRIC), moyenne 0-30 cm, résolution 250 m",
              "tn": "SoilGrids 2.0 (ISRIC)، معدّل 0-30 صم، دقّة 250 م", "ja": "SoilGrids 2.0（ISRIC）、0～30 cm平均、250 m解像度"},
 "s.src.default": {"fr": "PROFIL PAR DÉFAUT (SoilGrids inaccessible) — choisissez votre type de sol",
                   "tn": "تربة افتراضية (SoilGrids ما خدمش) — اختار نوع أرضك", "ja": "既定値（SoilGridsに接続できません）— 土壌の種類を選んでください"},
 # satellite
 "sat.offline": {"fr": "mode hors ligne", "tn": "بلاش أنترنات", "ja": "オフラインモード"},
 "sat.lib": {"fr": "bibliothèque manquante ({x})", "tn": "مكتبة ناقصة ({x})", "ja": "ライブラリ不足（{x}）"},
 "sat.none": {"fr": "aucune image Sentinel-2 exploitable", "tn": "ما فماش تصاور Sentinel-2 صالحة", "ja": "利用可能なSentinel-2画像がありません"},
 "sat.down": {"fr": "Planetary Computer inaccessible ({x})", "tn": "Planetary Computer ما يجاوبش ({x})", "ja": "Planetary Computerに接続できません（{x}）"},
 "sat.cloud": {"fr": "images trop nuageuses sur la parcelle", "tn": "التصاور فيها برشا سحاب", "ja": "圃場の画像が雲で覆われています"},
 "sat.i.none": {"fr": "Pas de végétation active détectée : parcelle en jachère, nue ou non irriguée.",
                "tn": "ما فماش نبات أخضر: الأرض بور ولا عريانة ولا موش مسقية.",
                "ja": "活発な植生は検出されません：休耕地、裸地、または無灌漑です。"},
 "sat.i.active": {"fr": "Végétation active {n} mois sur {total} observés (NDVI > 0,35) : parcelle déjà cultivée.",
                  "tn": "الأرض خضراء {n} شهر من {total} (NDVI > 0.35): مزروعة من قبل.",
                  "ja": "観測{total}か月中{n}か月で植生が活発（NDVI > 0.35）：すでに耕作されています。"},
 "sat.i.high": {"fr": "Vigueur maximale élevée : bon potentiel de sol et d'eau à certaines saisons.",
                "tn": "النبات يوصل لقوّة كبيرة: الأرض والماء فيهم خير في بعض المواسم.",
                "ja": "最大活力が高い：季節によって土壌と水の潜在力が高いです。"},
 "sat.i.low": {"fr": "Vigueur maximale faible : sol pauvre, sec ou peu exploité.",
               "tn": "النبات ضعيف: الأرض فقيرة ولا شايحة ولا ما تتخدمش برشا.",
               "ja": "最大活力が低い：やせた土地、乾燥、または未利用です。"},
 "sat.i.het": {"fr": "Parcelle hétérogène : les zones de vigueur servent à placer les cultures exigeantes au meilleur endroit.",
               "tn": "الأرض موش كيف كيف: نحطّو الزرايع اللي تستحقّ برشا في البلايص الأقوى.",
               "ja": "圃場にばらつきあり：要求の高い作物を最も良い区画に配置します。"},
 "sat.i.green_summer": {"fr": "Parcelle verte même en été : arbres déjà en place ou irrigation.",
                        "tn": "الأرض خضراء حتى في الصيف: فيها شجر ولا تتسقى.",
                        "ja": "夏でも緑：すでに樹木があるか、灌漑されています。"},
 # climat
 "c.src.power": {"fr": "NASA POWER, données journalières {a}-{b}", "tn": "NASA POWER، معطيات يومية {a}-{b}", "ja": "NASA POWER 日別データ {a}～{b}"},
 "c.src.demo": {"fr": "HISTORIQUE DE DÉMONSTRATION (normales de {x}, NASA POWER inaccessible) — ne pas utiliser pour une vraie décision",
                "tn": "معطيات تجريبية (معدّلات {x}، NASA POWER ما خدمش) — ما تعتمدش عليها",
                "ja": "デモ用データ（{x}の平年値、NASA POWERに接続不可）— 実際の判断には使わないでください"},
 "c.pm": {"fr": "FAO-56 Penman-Monteith", "tn": "FAO-56 Penman-Monteith", "ja": "FAO-56 ペンマン・モンティース式"},
 "c.hg": {"fr": "Hargreaves (FAO-56 éq. 52)", "tn": "Hargreaves (FAO-56)", "ja": "ハーグリーブス式（FAO-56）"},
 # avertissements
 "w.demo": {"fr": "Météo historique NASA POWER inaccessible : résultats en mode démonstration.",
            "tn": "ما نجّمناش نجيبو الطقس من NASA POWER: النتايج تجريبية برك.",
            "ja": "NASA POWERの気象データに接続できません：デモ結果です。"},
 "w.soil": {"fr": "Sol non mesuré (SoilGrids inaccessible) : indiquez votre type de sol pour un résultat fiable.",
            "tn": "ما نجّمناش نقيسو الأرض (SoilGrids): اختار نوع أرضك باش النتيجة تكون صحيحة.",
            "ja": "土壌を測定できません（SoilGrids不可）：正確な結果のため土壌の種類を選んでください。"},
 "w.sat": {"fr": "Analyse satellite indisponible ({x}).", "tn": "تحليل الساتليت موش متوفّر ({x}).", "ja": "衛星解析は利用できません（{x}）。"},
 "w.green_rainfed": {"fr": "Le satellite montre une parcelle verte en plein été ({ndvi}). En culture en sec c'est rare : la parcelle est peut-être déjà plantée d'arbres ou irriguée. Vérifiez votre réponse sur l'eau.",
                     "tn": "الساتليت يورّي الأرض خضراء في الصيف ({ndvi}). بالمطر برك هذا قليل: يمكن فيها شجر ولا تتسقى. ثبّت في جوابك على الماء.",
                     "ja": "衛星では真夏でも緑（{ndvi}）。天水栽培では珍しく、すでに樹木があるか灌漑されている可能性があります。水の回答を確認してください。"},
 # erreurs
 "e.polygon": {"fr": "La parcelle doit être un polygone.", "tn": "لازم الأرض تكون مرسومة كمضلّع.", "ja": "圃場は多角形である必要があります。"},
 "e.corners": {"fr": "La parcelle doit avoir au moins 3 coins.", "tn": "لازم الأرض يكون فيها 3 زوايا على الأقل.", "ja": "圃場には少なくとも3つの角が必要です。"},
 "e.small": {"fr": "Parcelle trop petite (moins de 500 m²).", "tn": "الأرض صغيرة برشا (أقل من 500 م²).", "ja": "圃場が小さすぎます（500 m²未満）。"},
 "e.big": {"fr": "Parcelle trop grande (plus de 2 000 ha) : dessinez une seule exploitation.", "tn": "الأرض كبيرة برشا (أكثر من 2000 هك): ارسم ضيعة وحدة.", "ja": "圃場が大きすぎます（2,000 ha超）：1つの農場だけを描いてください。"},
 "e.zone": {"fr": "Zone non couverte : MIZU KIZUNA fonctionne pour la Tunisie et le Japon.", "tn": "المنطقة هاذي موش مغطّية: MIZU KIZUNA يخدم في تونس واليابان.", "ja": "対象外の地域です：MIZU KIZUNAはチュニジアと日本に対応しています。"},
 "e.crop": {"fr": "Culture inconnue pour ce pays.", "tn": "الزرعة هاذي موش معروفة في البلاد هاذي.", "ja": "この国では未登録の作物です。"},
 # prévisions
 "f.na": {"fr": "Prévisions indisponibles pour le moment.", "tn": "التوقّعات موش متوفّرة توّا.", "ja": "現在、予報は利用できません。"},
 "f.sum": {"fr": "16 prochains jours : de {tmin} °C à {tmax} °C, {rain} mm de pluie prévus.",
           "tn": "الـ16 يوم الجايين: من {tmin} لـ{tmax} درجة، {rain} مم مطر متوقّع.",
           "ja": "今後16日間：{tmin}～{tmax} °C、降水量{rain} mmの予報。"},
 "f.frost": {"fr": "{crop} : gel possible ({t} °C), attendre avant de {act}.", "tn": "{crop}: ينجم يجي الجليد ({t} درجة)، استنّى قبل ما {act}.", "ja": "{crop}：霜の恐れ（{t} °C）。{act}のは待ちましょう。"},
 "f.heat": {"fr": "{crop} : forte chaleur annoncée (moyenne {t} °C), retarder.", "tn": "{crop}: سخانة كبيرة جاية (معدّل {t} درجة)، أخّر شويّة.", "ja": "{crop}：猛暑の予報（平均{t} °C）。遅らせましょう。"},
 "f.good": {"fr": "{crop} : conditions favorables pour {act} dans les prochains jours.", "tn": "{crop}: الطقس مناسب باش {act} في الأيام الجاية.", "ja": "{crop}：数日以内に{act}のに良い条件です。"},
 "f.rain": {"fr": "Pluie significative annoncée : retarder le premier arrosage.", "tn": "فما مطر مليح جاي: أخّر أوّل سقية.", "ja": "まとまった雨の予報：最初の灌水を遅らせましょう。"},
 "act.sow": {"fr": "semer", "tn": "تزرع", "ja": "種をまく"},
 "act.plant": {"fr": "planter", "tn": "تغرس", "ja": "植え付ける"},
 # plan / carte
 "m.unplanted": {"fr": "non planté (eau insuffisante)", "tn": "موش مزروع (الماء ما يكفيش)", "ja": "未作付け（水不足）"},
 "m.unplanted_short": {"fr": "non planté", "tn": "موش مزروع", "ja": "未作付け"},
 "m.rainfed": {"fr": "en sec", "tn": "بالمطر", "ja": "天水"},
 "m.place_zones": {"fr": "zones de vigueur Sentinel-2", "tn": "مناطق القوّة من Sentinel-2", "ja": "Sentinel-2の活力ゾーン"},
 "m.place_strips": {"fr": "bandes (pas de zones satellite)", "tn": "شرايط (ما فماش مناطق من الساتليت)", "ja": "帯状配置（衛星ゾーンなし）"},
 # compatibilité
 "co.same_family": {"fr": "même famille ({fam}) : ravageurs et maladies partagés", "tn": "نفس العايلة ({fam}): نفس الحشرات والأمراض", "ja": "同じ科（{fam}）：害虫・病気が共通"},
 "co.water_diff": {"fr": "besoins en eau très différents", "tn": "يستحقّو كميّات ماء مختلفة برشا", "ja": "必要水量が大きく異なる"},
 "co.roots": {"fr": "racines à profondeurs différentes (moins de concurrence)", "tn": "العروق في أعماق مختلفة (ما يتزاحموش)", "ja": "根の深さが異なる（競合が少ない）"},
 "co.shade_ok": {"fr": "{low} supporte l'ombre partielle de {tall}", "tn": "{low} تتحمّل ظلّ {tall}", "ja": "{low}は{tall}の半日陰に耐えます"},
 "co.shade_bad": {"fr": "{tall} fait de l'ombre à {low}", "tn": "{tall} يعمل الظلّ على {low}", "ja": "{tall}が{low}を日陰にします"},
 "co.no_overlap": {"fr": "pas en place en même temps : plutôt en rotation qu'ensemble", "tn": "ما يكونوش في الأرض في نفس الوقت: الأحسن بالتداول", "ja": "同時期に栽培しない：混植より輪作向き"},
 "co.generic_src": {"fr": "règles agronomiques générales", "tn": "قواعد فلاحية عامّة", "ja": "一般的な農学的ルール"},
 "co.intercrop": {"fr": "entre les rangs, surtout en jeune plantation", "tn": "بين الخطوط، خاصّة كي يكون الشجر صغير", "ja": "列間に。特に若木のうちに"},
 "conf.high": {"fr": "élevée", "tn": "عالية", "ja": "高"}, "conf.medium": {"fr": "moyenne", "tn": "متوسّطة", "ja": "中"},
 "conf.low": {"fr": "faible", "tn": "ضعيفة", "ja": "低"},
 # combinaisons
 "cb.needs_irrig": {"fr": "demande de l'irrigation : impossible en culture en sec", "tn": "تستحقّ السقي: ما تنجمش بالمطر برك", "ja": "灌漑が必要：天水栽培では不可"},
 "cb.weak_member": {"fr": "{crop} est peu adapté à votre parcelle (score {s}/100)", "tn": "{crop} موش مناسبة برشا لأرضك (سكور {s}/100)", "ja": "{crop}はこの圃場にあまり適していません（スコア{s}/100）"},
 "cb.water_ok": {"fr": "Eau estimée : {need} m³/ha/an — votre eau suffit.", "tn": "الماء المقدّر: {need} م³/هك/العام — الماء متاعك يكفي.", "ja": "推定必要水量：{need} m³/ha/年 — 水量は足ります。"},
 "cb.water_part": {"fr": "Eau estimée : {need} m³/ha/an — avec votre eau, possible sur environ {ha} ha.", "tn": "الماء المقدّر: {need} م³/هك/العام — بالماء متاعك تنجم تعملها في حوالي {ha} هك.", "ja": "推定必要水量：{need} m³/ha/年 — 現在の水量では約{ha} haで可能です。"},
 "cb.water_need": {"fr": "Eau estimée : {need} m³/ha/an (indiquez votre quantité d'eau pour savoir sur combien d'hectares).", "tn": "الماء المقدّر: {need} م³/هك/العام (اكتب قدّاش عندك ماء باش نقولولك على قدّاش من هكتار).", "ja": "推定必要水量：{need} m³/ha/年（水量を入力すると何ha可能か分かります）。"},
 "cb.role.top": {"fr": "étage haut", "tn": "الطبقة الفوقانية", "ja": "上層"},
 "cb.role.middle": {"fr": "étage moyen", "tn": "الطبقة الوسطى", "ja": "中層"},
 "cb.role.low": {"fr": "au sol / entre les rangs", "tn": "في الأرض / بين الخطوط", "ja": "地表・列間"},
 "cb.role.first": {"fr": "d'abord (hiver)", "tn": "الأوّل (الشتاء)", "ja": "先作（冬）"},
 "cb.role.then": {"fr": "ensuite (été)", "tn": "من بعد (الصيف)", "ja": "後作（夏）"},
 "cb.water.both": {"fr": "en sec ou irrigué", "tn": "بالمطر ولا بالسقي", "ja": "天水・灌漑どちらも可"},
 "cb.water.irrigated": {"fr": "irrigué seulement", "tn": "بالسقي برك", "ja": "灌漑のみ"},
 "cb.water.rainfed": {"fr": "en sec", "tn": "بالمطر", "ja": "天水"},
 "cb.cause.etages": {"fr": "Étages", "tn": "الطبقات", "ja": "階層"},
 "cb.cause.racines": {"fr": "Racines", "tn": "العروق", "ja": "根"},
 "cb.cause.azote": {"fr": "Azote", "tn": "الآزوت", "ja": "窒素"},
 "cb.cause.ravageurs": {"fr": "Insectes", "tn": "الحشرات", "ja": "害虫・益虫"},
 "cb.cause.eau": {"fr": "Eau", "tn": "الماء", "ja": "水"},
 "cb.cause.sol": {"fr": "Sol", "tn": "الأرض", "ja": "土壌"},
 "cb.cause.revenu": {"fr": "Revenu", "tn": "الدخل", "ja": "収入"},
 "cb.cause.calendrier": {"fr": "Calendrier", "tn": "الرزنامة", "ja": "作期"},
 "cb.cause.microclimat": {"fr": "Microclimat", "tn": "المناخ المحلّي", "ja": "微気象"},
 "method": {"fr": "Score = climat × sol × sel × eau × (1 − risque), calculé sur chaque année de l'historique météo. Exigences des cultures : FAO EcoCrop (seuils de pluie en sec calibrés sur la pratique tunisienne) ; besoins en eau : FAO-56 ; salinité : FAO-29 ; sol : SoilGrids ; parcelle : Sentinel-2. Aide à la décision : à confirmer avec un technicien agricole.",
            "tn": "السكور = الطقس × الأرض × الملح × الماء × (1 − الخطر)، محسوب على كل عام من تاريخ الطقس. حاجيات الزرايع: FAO EcoCrop (حدود المطر معدّلة على الفلاحة التونسية)؛ الماء: FAO-56؛ الملوحة: FAO-29؛ الأرض: SoilGrids؛ الضيعة: Sentinel-2. هاذي مساعدة على القرار: ثبّت مع تقني فلاحي (CRDA).",
            "ja": "スコア＝気候×土壌×塩分×水×（1－リスク）を過去の各年について計算。作物要件：FAO EcoCrop（天水の降水量基準はチュニジアの実態に合わせて補正）、必要水量：FAO-56、塩分：FAO-29、土壌：SoilGrids、圃場：Sentinel-2。意思決定の支援ツールです。普及指導員にもご確認ください。"},
}

FAMILIES = {
 "Solanacées": ("الباذنجانيات", "ナス科"), "Alliacées": ("البصليات", "ヒガンバナ科（ネギ属）"), "Cucurbitacées": ("القرعيات", "ウリ科"),
 "Apiacées": ("الخيميات", "セリ科"), "Astéracées": ("المركّبات", "キク科"), "Brassicacées": ("الصليبيات", "アブラナ科"),
 "Poacées": ("النجيليات", "イネ科"), "Fabacées": ("البقوليات", "マメ科"), "Convolvulacées": ("العليقيات", "ヒルガオ科"),
 "Rosacées": ("الورديات", "バラ科"), "Oléacées": ("الزيتونيات", "モクセイ科"), "Arécacées": ("النخيليات", "ヤシ科"),
 "Rutacées": ("السذابيات (القوارص)", "ミカン科"), "Vitacées": ("الكرميات", "ブドウ科"), "Moracées": ("التوتيات", "クワ科"),
 "Lythracées": ("الحنّائيات", "ミソハギ科"), "Lamiacées": ("الشفويات", "シソ科"), "Anacardiacées": ("البطميات", "ウルシ科"), "Théacées": ("الشائيات", "ツバキ科"),
}

TEXTURES = {
 "sable": ("رمل", "砂土"), "sable limoneux": ("رمل طميي", "壌質砂土"), "limon sableux": ("طمي رملي", "砂壌土"),
 "limon": ("طمي", "壌土"), "limon fin": ("طمي ناعم", "シルト質壌土"), "silt": ("سلت", "シルト"),
 "limon argilo-sableux": ("طمي طيني رملي", "砂質埴壌土"), "limon argileux": ("طمي طيني", "埴壌土"),
 "limon argilo-fin": ("طمي طيني ناعم", "シルト質埴壌土"), "argile sableuse": ("طين رملي", "砂質埴土"),
 "argile limoneuse": ("طين طميي", "シルト質埴土"), "argile": ("طين", "埴土"),
}

# mécanismes des compatibilités (texte français du fichier companions.csv → tn, ja)
MECH = {
 "racines à profondeurs différentes, la carotte occupe l'interligne": ("العروق في أعماق مختلفة، والسفنارية تعمّر بين الخطوط", "根の深さが異なり、ニンジンが畝間を活用"),
 "l'odeur de l'oignon gêne certains ravageurs": ("ريحة البصل تبعّد بعض الحشرات", "タマネギの匂いが一部の害虫を遠ざける"),
 "la laitue basse profite de l'ombre de la tomate": ("الخسّ القصير يستفاد من ظلّ الطماطم", "背の低いレタスがトマトの日陰を活用"),
 "même famille : mildiou et ravageurs communs": ("نفس العايلة: الميلديو ونفس الحشرات", "同じ科：疫病と害虫が共通"),
 "même famille : maladies communes": ("نفس العايلة: نفس الأمراض", "同じ科：病気が共通"),
 "incompatibles selon les guides de vulgarisation": ("موش متوافقين حسب أدلّة الإرشاد الفلاحي", "普及資料によると相性が悪い"),
 "légumineuse fixatrice d'azote": ("بقولية تثبّت الآزوت في الأرض", "窒素を固定するマメ科"),
 "associés dans les guides de vulgarisation": ("ينصحو بيهم مع بعضهم في أدلّة الإرشاد", "普及資料で推奨される組み合わせ"),
 "concurrence et maladies communes": ("يتزاحمو وعندهم نفس الأمراض", "競合し、病気も共通"),
 "cultures compatibles, besoins proches": ("زرايع متوافقة وحاجياتها قريبة", "相性が良く、必要条件も近い"),
 "association classique : l'oignon éloigne la mouche de la carotte et inversement": ("تركيبة معروفة: البصل يبعّد ذبانة السفنارية والعكس", "定番の組み合わせ：タマネギとニンジンが互いの害虫を遠ざける"),
 "cultures basses compatibles, cycles proches": ("زرايع قصيرة متوافقة ومدّتها قريبة", "背の低い作物同士で生育期間も近い"),
 "l'oignon gêne certains ravageurs du chou": ("البصل يبعّد بعض حشرات الكرنب", "タマネギがキャベツの害虫を遠ざける"),
 "les alliacées freinent la croissance des légumineuses": ("البصل والثوم يعطّلو نموّ البقوليات", "ネギ類はマメ科の生育を妨げる"),
 "l'ail limite certains ravageurs": ("الثوم ينقّص بعض الحشرات", "ニンニクが一部の害虫を抑える"),
 "profondeurs et cycles compatibles": ("الأعماق والمدّة متوافقين", "根の深さと生育期間が合う"),
 "légumineuse + racine pivot": ("بقولية + عرق طويل", "マメ科＋直根"),
 "cultures basses compatibles": ("زرايع قصيرة متوافقة", "背の低い作物同士で相性が良い"),
 "racines concurrentes à la même profondeur": ("العروق يتزاحمو في نفس العمق", "根が同じ深さで競合"),
 "la laitue profite de l'ombre légère": ("الخسّ يحبّ الظلّ الخفيف", "レタスは軽い日陰を好む"),
 "cycles courts compatibles": ("زرايع قصيرة المدّة متوافقة", "短期作物同士で相性が良い"),
 "cycle court qui occupe l'interligne": ("زرعة قصيرة تعمّر بين الخطوط", "短期作物で畝間を活用"),
 "même famille : ravageurs communs (altises, piérides)": ("نفس العايلة: نفس الحشرات", "同じ科：害虫が共通（ノミハムシ、モンシロチョウ）"),
 "la légumineuse enrichit le sol en azote": ("البقولية تزيد الآزوت للأرض", "マメ科が土壌に窒素を供給"),
 "le radis repousse certains ravageurs du concombre": ("الفجل يبعّد بعض حشرات الخيار", "ダイコンがキュウリの害虫を遠ざける"),
 "même famille : oïdium et ravageurs communs": ("نفس العايلة: الرمد الأبيض ونفس الحشرات", "同じ科：うどんこ病と害虫が共通"),
 "association céréale-légumineuse : azote et meilleure utilisation des ressources": ("حبوب + بقول: آزوت واستعمال أحسن للأرض والماء", "穀物＋マメ科：窒素供給と資源の有効利用"),
 "association céréale-légumineuse classique (fourrage, grain)": ("حبوب + بقول معروفة (علف وحبّ)", "定番の穀物＋マメ科（飼料・子実）"),
 "association céréale-légumineuse": ("حبوب + بقول", "穀物＋マメ科の組み合わせ"),
 "rotation et association céréale-légumineuse": ("تداول وتركيبة حبوب + بقول", "穀物とマメ科の輪作・混作"),
 "culture intercalaire en oliveraie, apport d'azote": ("زرعة بين الزيتون، تزيد الآزوت", "オリーブ園の間作、窒素供給"),
 "culture intercalaire en oliveraie pluviale": ("زرعة بين الزيتون البعلي", "天水オリーブ園の間作"),
 "culture intercalaire en oliveraie": ("زرعة بين الزيتون", "オリーブ園の間作"),
 "forte concurrence pour l'eau en zone sèche": ("يتزاحمو برشا على الماء في المناطق الشايحة", "乾燥地で水を激しく奪い合う"),
 "culture intercalaire en jeune verger": ("زرعة بين الشجر الصغير", "若い果樹園の間作"),
 "culture intercalaire en jeune verger, apport d'azote": ("زرعة بين الشجر الصغير، تزيد الآزوت", "若い果樹園の間作、窒素供給"),
 "culture intercalaire en jeune verger pluvial": ("زرعة بين الشجر الصغير البعلي", "天水の若い果樹園の間作"),
 "oasis à étages : fourrage sous les palmiers": ("الواحة بالطبقات: العلف تحت النخيل", "階層型オアシス：ヤシの下で飼料作物"),
 "oasis à étages : arbres fruitiers sous les palmiers": ("الواحة بالطبقات: الشجر المثمر تحت النخيل", "階層型オアシス：ヤシの下で果樹"),
 "oasis à étages : agrumes protégés par le palmier": ("الواحة بالطبقات: القوارص في حماية النخلة", "階層型オアシス：ヤシに守られた柑橘"),
 "étage bas de l'oasis": ("الطبقة اللوطانية في الواحة", "オアシスの下層"),
 "maraîchage sous palmiers (étage bas)": ("خضرة تحت النخيل (الطبقة اللوطانية)", "ヤシの下での野菜栽培（下層）"),
 "étage bas de l'oasis, surveiller l'eau": ("الطبقة اللوطانية في الواحة، رد بالك على الماء", "オアシスの下層、水管理に注意"),
 "enherbement temporaire possible": ("تنجم تخلّي حشيش مؤقّت", "一時的な草生栽培が可能"),
 "rotation rizière / soja courante au Japon (pas en même temps)": ("تداول روز / صوجا معروف في اليابان (موش في نفس الوقت)", "日本で一般的な水田・大豆の輪作（同時ではない）"),
 "double culture blé d'hiver puis soja au Japon (successives)": ("في اليابان: قمح شتوي ومن بعد صوجا", "日本の麦・大豆の二毛作（連続栽培）"),
 "couvre-sol + légumineuse": ("زرعة تغطّي الأرض + بقولية", "地表被覆作物＋マメ科"),
 "culture intercalaire en jeune théier": ("زرعة بين التاي الصغير", "若い茶園の間作"),
}


REGION_NAMES = {
 "nord-ouest": ("الشمال الغربي", "北西部"), "cap bon et nord-est": ("الوطن القبلي والشمال الشرقي", "ボン岬・北東部"),
 "sahel et Sfax": ("الساحل وصفاقس", "サヘル・スファックス"), "centre": ("الوسط", "中部"),
 "oasis du sud-ouest": ("واحات الجنوب الغربي", "南西部のオアシス"), "sud-est": ("الجنوب الشرقي", "南東部"),
 "Kantō (Ibaraki)": ("كانتو (إيباراكي)", "関東（茨城）"), "Hokkaidō": ("هوكايدو", "北海道"),
 "Tōhoku et Niigata": ("توهوكو ونيغاتا", "東北・新潟"), "Shizuoka et Tōkai": ("شيزوكا وتوكاي", "静岡・東海"),
 "Kansai": ("كانساي", "関西"), "Kyūshū": ("كيوشو", "九州"),
}


def region_name(fr):
    l = lang()
    return fr if l == "fr" else REGION_NAMES.get(fr, (fr, fr))[0 if l == "tn" else 1]


def lang():
    return LANG.get()


def t(key, **kw):
    entry = M.get(key)
    if not entry:
        return key
    txt = entry.get(lang()) or entry["fr"]
    return txt.format(**kw) if kw else txt


def crop_name(c):
    return c.get("names", {}).get(lang()) or c["name_fr"]


def family(fr):
    l = lang()
    return fr if l == "fr" else FAMILIES.get(fr, (fr, fr))[0 if l == "tn" else 1]


def texture(fr):
    l = lang()
    return fr if l == "fr" else TEXTURES.get(fr, (fr, fr))[0 if l == "tn" else 1]


def mechanism(fr):
    l = lang()
    return fr if l == "fr" else MECH.get(fr, (fr, fr))[0 if l == "tn" else 1]


def months(l=None):
    l = l or lang()
    return {"fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
            "tn": ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
            "ja": [f"{i}月" for i in range(1, 13)]}[l]
