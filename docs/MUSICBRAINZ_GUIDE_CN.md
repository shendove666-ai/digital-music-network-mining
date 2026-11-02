# 用 MusicBrainz 重建可核验合作网络

## 研究口径

本项目只把“同时出现在同一条 MusicBrainz recording 的 artist credit 中”定义为合作。边权重是两位艺术家共同署名的不同 recording MBID 数量。

这一定义不会把同一合辑里互不合作的艺术家连在一起，也不会自动把作曲、制作、采样或现场同台当成录音合作。若以后研究这些关系，应另建关系类型和证据规则，不能混入本数据。

## 第一步：生成40位候选艺术家

```powershell
python musicbrainz_provenance.py prepare --top 40
```

输出：`data/musicbrainz/artist_registry.csv`。

这40人按旧数据中的连接数筛选，只用于确定一个可管理的检索范围；旧关系和旧权重不会被当作证据。

## 第二步：搜索身份候选

```powershell
python musicbrainz_provenance.py search
```

输出：`data/musicbrainz/artist_candidates.csv`。每位艺术家最多有5个候选，包含 MBID、国家、类型和消歧说明。

不要因为某个候选排第一就自动确认。打开候选的 MusicBrainz URL，核对姓名、国家、乐队/个人类型和消歧说明。

## 第三步：人工确认身份

打开 `artist_registry.csv`，逐行填写：

- `artist_mbid`：确认后的 MusicBrainz Artist MBID；
- `canonical_name`：MusicBrainz 上的规范名称；
- `disambiguation`：候选的消歧说明；
- `confirmation_status`：只允许 `confirmed` 或 `excluded`；
- `review_note`：为什么确认或排除，例如“Japanese composer, born 1952”。

有歧义又无法确认时选择 `excluded`，不要猜。

## 第四步：抓取录音证据并生成边表

```powershell
python musicbrainz_provenance.py collect
```

输出：

- `recording_evidence.csv`：每一行是一条共同署名录音证据，保存双方 MBID、录音 MBID、发行 MBID、日期和链接；
- `verified_artist_edgelist.csv`：按艺术家对聚合，`Weight` 等于不同共同署名 recording MBID 数量；
- `cache/`：API缓存，仅用于断点续跑，不提交到 GitHub。

## 第五步：先审计，再分析

随机打开至少20条 `recording_url`，并重点检查网络中心性最高的艺术家。确认无误后运行：

```powershell
python music_network_mining.py --mode real `
  --input data/musicbrainz/verified_artist_edgelist.csv `
  --artist-registry data/musicbrainz/artist_registry.csv `
  --gexf output/musicbrainz_verified_network.gexf `
  --csv output/musicbrainz_verified_metrics.csv
```

随后以保持每位艺术家连接数不变的随机网络作为基准：

```powershell
python null_model_analysis.py `
  --input data/musicbrainz/verified_artist_edgelist.csv `
  --artist-registry data/musicbrainz/artist_registry.csv `
  --repetitions 500 `
  --output-dir output/musicbrainz_null_model
```

旧项目的120个节点、260条边及全部指标不能沿用。README、简历和个人陈述只能引用重建后的真实结果。
