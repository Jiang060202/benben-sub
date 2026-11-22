# benben-sub（私人订阅，仅自用）

自动收集网上公开的免费节点配置，生成一个订阅链接，导入 V2Box 就能用。
每小时自动更新一次。

思路来自俄罗斯的 anti-RKN 仓库 [aneek0/goida-vpn-configs](https://github.com/aneek0/goida-vpn-configs)，
来源也是它那 24 个公开收集仓库（去掉了 1 个已失效的）。

## 订阅链接（加到 V2Box）

主用（jsDelivr，国内不用翻墙就能打开）：

```
https://cdn.jsdelivr.net/gh/Jiang060202/benben-sub@main/sub.txt
```

备用（GitHub raw）：

```
https://raw.githubusercontent.com/Jiang060202/benben-sub/main/sub.txt
```

V2Box 里：订阅 → 添加订阅 → 粘贴链接 → 更新订阅。

## 分组订阅（一次只导一小批）

5000 个节点分成 100 组，每组 50 个。嫌一次导 5000 个太多，就导一组，测完再换下一组。

分组链接格式（001 到 100）：

```
https://cdn.jsdelivr.net/gh/Jiang060202/benben-sub@main/sub-001.txt
```

也可以直接打开展示页，点复制、翻页：

```
https://jiang060202.github.io/benben-sub/
```

（GitHub Pages 在国内打不开，看页面要开着节点；订阅链接本身走 jsDelivr，国内能用。）

## 说明

- 来源是 24 个公开收集仓库（GitHub 上别人分享的免费配置），这里每小时汇总一次。
- 节点按协议排过序：VLESS / Trojan / Hysteria2 / TUIC 在前面。
- 免费公开节点质量参差，死的很多：导入后在 V2Box 里测速，挑能用的连；死的下次更新会自动换掉。
- ⚠️ 流量经过陌生人的服务器，别用它登录账号、付钱、收验证码；只用来看视频、刷网页。
- 仓库是公开的，但里面没有任何你自己的东西（没有你自己的节点、密码），不宣传就没人知道。
  公开是故意的：只有公开仓库，V2Box 才能直接拉订阅（私密仓库要带密码，反而不好用）。

## 文件

- `collect.py` 收集脚本（只用 Python 标准库）
- `.github/workflows/update.yml` 每小时自动跑
- `sub.txt` 订阅（base64，5000 条）
- `sub_plain.txt` 明文节点列表
- `sub-001.txt` … `sub-100.txt` 分组订阅（每组 50 条）
- `stats.json` 统计（更新时间、各协议数量、分组列表）
