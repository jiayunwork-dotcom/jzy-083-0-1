"""薄膜光学特征矩阵核算服务。

模块分工：
- admittance  光学导纳与 s/p 偏振
- matrix      复数特征矩阵的构造与连乘
- solver      单波长单角度下 R/T/A 的求解
- spectrum    波长扫描
- validation  输入合法性校验与膜系解析
- demo        内置示范膜系
- server      Flask HTTP 接口层
"""
