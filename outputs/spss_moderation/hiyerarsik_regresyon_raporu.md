# Hiyerarsik Coklu Regresyon Analizi

Veri dosyasi: `C:\Users\Melih Kalkan\Downloads\Melisa Spss Araştırma Yöntemleri 2\spss yemi versiyon.sav`

Puanlama: OZY maddelerinde 2, 4, 5, 6, 7, 10, 11, 12, 14, 16, 17; GK maddelerinde 2, 4, 6, 8, 10, 12 ters puanlandi. BTO-12'de ters madde yoktur. Regresyon analizinde olcek ortalama puanlari kullanildi.

Analize dahil edilen gecerli gozlem sayisi: **76**.

## Guvenirlik
| Olcek | Madde | Cronbach_alpha |
| --- | --- | --- |
| Oz-yeterlilik | 17 | 0.8322 |
| Gelecek kaygisi | 19 | 0.9029 |
| Belirsizlige tahammulsuzluk | 12 | 0.8744 |

## Betimsel Istatistikler
| Degisken | N | Ortalama | SS | Min | Max | Carpiklik | Basıklık |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Belirsizlige tahammulsuzluk | 76 | 3.0735 | 0.8099 | 1.0000 | 4.7500 | -0.3800 | -0.1270 |
| Oz-yeterlilik | 76 | 3.7221 | 0.5359 | 1.9412 | 4.9412 | -0.3678 | 0.8247 |
| Gelecek kaygisi | 76 | 2.8102 | 0.7417 | 1.3684 | 4.4737 | 0.0525 | -0.5934 |

## Korelasyonlar
| Degisken_1 | Degisken_2 | r | p | p_format |
| --- | --- | --- | --- | --- |
| Belirsizlige tahammulsuzluk | Belirsizlige tahammulsuzluk | 1.0000 |  |  |
| Belirsizlige tahammulsuzluk | Oz-yeterlilik | -0.4249 | 0.0001 | < .001 |
| Belirsizlige tahammulsuzluk | Gelecek kaygisi | 0.5804 | 0.0000 | < .001 |
| Oz-yeterlilik | Belirsizlige tahammulsuzluk | -0.4249 | 0.0001 | < .001 |
| Oz-yeterlilik | Oz-yeterlilik | 1.0000 |  |  |
| Oz-yeterlilik | Gelecek kaygisi | -0.5955 | 0.0000 | < .001 |
| Gelecek kaygisi | Belirsizlige tahammulsuzluk | 0.5804 | 0.0000 | < .001 |
| Gelecek kaygisi | Oz-yeterlilik | -0.5955 | 0.0000 | < .001 |
| Gelecek kaygisi | Gelecek kaygisi | 1.0000 |  |  |

## Model Ozeti
| Model | N | R | R2 | Duzeltilmis_R2 | F | df1 | df2 | p | p_format |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 76 | 0.6967 | 0.4854 | 0.4713 | 34.4305 | 2 | 73 | 0.0000 | < .001 |
| 2 | 76 | 0.6970 | 0.4858 | 0.4644 | 22.6748 | 3 | 72 | 0.0000 | < .001 |

## R Kare Degisimi
| Blok | R2_degisim | F_degisim | df1 | df2 | p | p_format |
| --- | --- | --- | --- | --- | --- | --- |
| 2 - etkilesim | 0.0004 | 0.0549 | 1 | 72 | 0.8154 | .815 |

## Katsayilar
| Model | Degisken | B | SH | Beta_std | t | p | p_format | CI95_alt | CI95_ust |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Sabit | 2.8102 | 0.0619 |  | 45.4286 | 0.0000 | < .001 | 2.6870 | 2.9335 |
| 1 | BTO_c | 0.3658 | 0.0849 | 0.3995 | 4.3071 | 0.0001 | < .001 | 0.1966 | 0.5351 |
| 1 | OZY_c | -0.5893 | 0.1284 | -0.4258 | -4.5909 | 0.0000 | < .001 | -0.8451 | -0.3335 |
| 2 | Sabit | 2.8186 | 0.0718 |  | 39.2541 | 0.0000 | < .001 | 2.6755 | 2.9617 |
| 2 | BTO_c | 0.3599 | 0.0892 | 0.3929 | 4.0335 | 0.0001 | < .001 | 0.1820 | 0.5377 |
| 2 | OZY_c | -0.5950 | 0.1314 | -0.4299 | -4.5262 | 0.0000 | < .001 | -0.8569 | -0.3330 |
| 2 | BTOxOZY | 0.0460 | 0.1965 | 0.0207 | 0.2343 | 0.8154 | .815 | -0.3456 | 0.4377 |

## Coklu Dogrusallik
| Degisken | VIF | Tolerance |
| --- | --- | --- |
| BTO_c | 1.3290 | 0.7525 |
| OZY_c | 1.2631 | 0.7917 |
| BTOxOZY | 1.0935 | 0.9145 |

## Kisa Yorum
Etkilesim terimi anlamli degildir; bu veri setinde oz-yeterliligin belirsizlige tahammulsuzluk ile gelecek kaygisi arasindaki iliskide istatistiksel olarak anlamli bir duzenleyici rol oynadigina dair kanit bulunmamistir.
