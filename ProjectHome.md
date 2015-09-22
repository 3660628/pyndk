Pyndk 是一个高效的，简单的，易使用的基于Python的网络开发框架。它借鉴了C++界强大
的网络开发库ACE，以Python的形式实现了高效，可复用的，异步网络处理框架。

## Features: ##

> `1.` 在不灵活和性能损失的情况下让网络开发更简单化，将网络层和业务层隔离开。

> `2.` 采用ACE中的Reactor模型，集成各平台(except windows)内最优的事件驱动器（目前只集成了epoll，poll， select)，windows平台使用select.

> `3.` 将定时器也集成到事件分离器中，完全单线程化

> `4.` 定时器框架将支持linux 下crontab 形式的定时器

> `5.` 完全异步连接、接收，最大化地使用系统CPU资源

> `6.` 每个反应器完全独立，你可以创建任意多个反应器（每个反应器要跑在独立的线程上）

> `7.` 反应器的接口线程安全。


## 评测： ##
使用ab 做为测试工具，网络环境为LOOPBACK(主要是测试框架的效率)

运行参数 ab -c 100 -n 10000 http://localhost:8000/

pyndk(单线程版本） 的测试结果
Requests per second:    9521.33 [#/sec](#/sec.md) (mean)


pyndk(多线程版本） 的测试结果
Requests per second:    7912.17 [#/sec](#/sec.md) (mean)


对应nginx/0.6.35的测试结果:
Requests per second:    6135.45 [#/sec](#/sec.md) (mean)


对应C＋＋版本的程序测试结果：
Requests per second:    10167.68 [#/sec](#/sec.md) (mean)
