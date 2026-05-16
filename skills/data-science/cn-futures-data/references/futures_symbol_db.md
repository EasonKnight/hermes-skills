# Chinese Futures Symbol Database (Sina Continuous Contracts)

All symbols use the "0" suffix convention: product code + "0" = continuous contract.
API call: `ak.futures_zh_daily_sina(symbol="CU0")`

## SHFE (上期所) - 17 products

| Symbol | Code | Name |
|--------|------|------|
| CU0 | 沪铜 | copper |
| AL0 | 沪铝 | aluminum |
| ZN0 | 沪锌 | zinc |
| PB0 | 沪铅 | lead |
| NI0 | 沪镍 | nickel |
| SN0 | 沪锡 | tin |
| AU0 | 沪金 | gold |
| AG0 | 沪银 | silver |
| RB0 | 螺纹钢 | rebar |
| HC0 | 热轧卷板 | hot-rolled coil |
| SS0 | 不锈钢 | stainless steel |
| BU0 | 沥青 | asphalt |
| RU0 | 橡胶 | rubber |
| FU0 | 燃料油 | fuel oil |
| SP0 | 纸浆 | pulp |
| WR0 | 线材 | wire rod |
| NR0 | 20号胶 | TSR20 (also in INE) |

## DCE (大商所) - 23 products

| Symbol | Code | Name |
|--------|------|------|
| C0 | 玉米 | corn |
| CS0 | 玉米淀粉 | corn starch |
| A0 | 豆一 | soybean #1 |
| B0 | 豆二 | soybean #2 |
| M0 | 豆粕 | soybean meal |
| Y0 | 豆油 | soybean oil |
| P0 | 棕榈油 | palm oil |
| FB0 | 纤维板 | fiberboard |
| BB0 | 胶合板 | plywood |
| JD0 | 鸡蛋 | egg |
| L0 | 聚乙烯(塑料) | LLDPE |
| PP0 | 聚丙烯 | polypropylene |
| V0 | PVC | PVC |
| EG0 | 乙二醇 | ethylene glycol |
| J0 | 焦炭 | coke |
| JM0 | 焦煤 | coking coal |
| I0 | 铁矿石 | iron ore |
| PG0 | 液化石油气 | LPG |
| EB0 | 苯乙烯 | styrene |
| RR0 | 粳米 | japonica rice |
| LH0 | 生猪 | live hog |
| LG0 | 原木 | log |
| BZ0 | 纯苯 | benzene |

## CZCE (郑商所) - 23 products

| Symbol | Code | Name |
|--------|------|------|
| TA0 | PTA | PTA |
| OI0 | 菜油 | rapeseed oil |
| RS0 | 菜籽 | rapeseed |
| RM0 | 菜粕 | rapeseed meal |
| WH0 | 强麦 | strong wheat (delisted ~2023) |
| JR0 | 粳稻 | japonica rice (delisted ~2022) |
| SR0 | 白糖 | white sugar |
| CF0 | 棉花 | cotton |
| ZC0 | 动力煤 | thermal coal (delisted ~2022) |
| FG0 | 玻璃 | glass |
| MA0 | 甲醇 | methanol |
| AP0 | 苹果 | apple |
| CJ0 | 红枣 | jujube |
| UR0 | 尿素 | urea |
| SA0 | 纯碱 | soda ash |
| SF0 | 硅铁 | ferrosilicon |
| SM0 | 锰硅 | manganese silicon |
| CY0 | 棉纱 | cotton yarn |
| PF0 | 短纤 | polyester staple fiber |
| PK0 | 花生 | peanut |
| LR0 | 晚籼稻 | late indica rice (delisted ~2022) |
| RI0 | 早籼稻 | early indica rice (delisted ~2022) |
| PM0 | 普麦 | common wheat (delisted ~2022) |

## CFFEX (中金所) - 8 products

| Symbol | Code | Name |
|--------|------|------|
| IF0 | 沪深300 | CSI 300 index futures |
| IC0 | 中证500 | CSI 500 index futures |
| IH0 | 上证50 | SSE 50 index futures |
| IM0 | 中证1000 | CSI 1000 index futures |
| T0 | 10年期国债 | 10y T-bond |
| TF0 | 5年期国债 | 5y T-bond |
| TS0 | 2年期国债 | 2y T-bond |
| TL0 | 30年期国债 | 30y T-bond |

## INE (上期能源) - 4 products

| Symbol | Code | Name |
|--------|------|------|
| SC0 | 原油 | crude oil |
| LU0 | 低硫燃料油 | low-sulfur fuel oil |
| BC0 | 国际铜 | copper (international) |
| NR0 | 20号胶 | TSR20 (also in SHFE) |

## GFEX (广期所) - 2 products

| Symbol | Code | Name |
|--------|------|------|
| SI0 | 工业硅 | industrial silicon |
| LC0 | 碳酸锂 | lithium carbonate |

## Alternative API for Full Exchange Data

To get ALL individual contract months (not just continuous):

```python
import akshare as ak
# All contracts traded on a specific date across an exchange
df = ak.get_futures_daily(start_date="2024-01-01", end_date="2024-01-31", market="DCE")
```
