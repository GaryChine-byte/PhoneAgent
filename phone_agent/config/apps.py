#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
App静态配置 - 143个预置应用的名称到包名映射

 提供开箱即用的常用应用配置，包括：
  - 社交通讯: 微信、QQ、钉钉、飞书、Telegram、WhatsApp、Slack、Teams、Zoom
  - 购物支付: 淘宝、京东、拼多多、支付宝、美团、Amazon、eBay
  - 视频娱乐: 抖音、TikTok、B站、小红书、快手、YouTube、Netflix、QQ音乐、Spotify
  - 地图导航: 高德地图、百度地图、腾讯地图、Google地图
  - 出行交通: 12306、滴滴出行、携程、去哪儿、飞猪
  - 金融银行: 云闪付、工行、中行、农行、建行、招行等11家银行
  - 政务服务: 国家反诈中心、个税、医保、交管12123
  - 浏览器: Chrome、Firefox、Edge、Opera、Brave、UC、夸克、QQ浏览器
  - 其他: AI助手、办公工具、云存储、输入法等

[NOTE] 使用方式:
  1. 直接调用: get_package_name("微信") → "com.tencent.mm"
  2. 动态配置: 通过前端"应用配置"页面添加/编辑应用
  3. 配置文件: 用户修改会保存到 data/app_config.json

 高级功能请使用 AppConfigManager:
  from phone_agent.config.app_manager import get_app_manager
  manager = get_app_manager()
  app = manager.find_app("微信")  # 支持别名、分类等
"""

APP_PACKAGES: dict[str, str] = {
    # ========================================
    # 系统工具 (System & Utilities)
    # ========================================
    "设置": "com.android.settings",
    "Settings": "com.android.settings",
    
    # ========================================
    # 社交通讯 (Social & Messaging)
    # ========================================
    "微信": "com.tencent.mm",
    "QQ": "com.tencent.mobileqq",
    "TIM": "com.tencent.tim",
    "企业微信": "com.tencent.wework",
    "QQ邮箱": "com.tencent.androidqqmail",
    "钉钉": "com.alibaba.android.rimet",
    "飞书": "com.ss.android.lark",
    "腾讯会议": "com.tencent.wemeet.app",
    "Telegram": "org.telegram.messenger",
    "WhatsApp": "com.whatsapp",
    "Slack": "com.Slack",
    "Discord": "com.discord",
    "Microsoft Teams": "com.microsoft.teams",
    "Zoom": "us.zoom.videomeetings",
    "Skype": "com.skype.raider",
    
    # ========================================
    # 电商购物 (E-commerce & Shopping)
    # ========================================
    "淘宝": "com.taobao.taobao",
    "京东": "com.jingdong.app.mall",
    "拼多多": "com.xunmeng.pinduoduo",
    "支付宝": "com.eg.android.AlipayGphone",
    "大麦": "cn.damai",
    "美团": "com.sankuai.meituan",
    "大众点评": "com.dianping.v1",
    "饿了么": "me.ele",
    "Amazon": "com.amazon.mShop.android.shopping",
    "eBay": "com.ebay.mobile",
    
    # ========================================
    # 视频娱乐 (Video & Entertainment)
    # ========================================
    "抖音": "com.ss.android.ugc.aweme",
    "TikTok": "com.zhiliaoapp.musically",
    "哔哩哔哩": "tv.danmaku.bili",
    "bilibili": "tv.danmaku.bili",
    "B站": "tv.danmaku.bili",
    "小红书": "com.xingin.xhs",
    "快手": "com.smile.gifmaker",
    "腾讯视频": "com.tencent.qqlive",
    "爱奇艺": "com.qiyi.video",
    "优酷": "com.youku.phone",
    "芒果TV": "com.hunantv.imgo.activity",
    "YouTube": "com.google.android.youtube",
    "Netflix": "com.netflix.mediaclient",
    "QQ音乐": "com.tencent.qqmusic",
    "网易云音乐": "com.netease.cloudmusic",
    "酷狗音乐": "com.kugou.android",
    "喜马拉雅": "com.ximalaya.ting.android",
    "Spotify": "com.spotify.music",
    
    # ========================================
    # 地图导航 (Maps & Navigation)
    # ========================================
    "高德地图": "com.autonavi.minimap",
    "百度地图": "com.baidu.BaiduMap",
    "腾讯地图": "com.tencent.map",
    "Google地图": "com.google.android.apps.maps",
    
    # ========================================
    # 出行交通 (Travel & Transportation)
    # ========================================
    "12306": "com.MobileTicket",
    "滴滴出行": "com.sdu.didi.psnger",
    "曹操出行": "com.caocaokeji.user",
    "T3出行": "com.t3go.passenger",
    "哈啰出行": "com.jingyao.easybike",
    "携程旅行": "ctrip.android.view",
    "去哪儿": "com.Qunar",
    "飞猪": "com.taobao.trip",
    
    
    # ========================================
    # 阅读学习 (Reading & Knowledge)
    # ========================================
    "微信读书": "com.tencent.weread",
    "有道词典": "com.youdao.dict",
    "扇贝单词": "cn.com.langeasy.LangEasyLexis",
    
    # ========================================
    # 办公工具 (Productivity & Office)
    # ========================================
    "WPS": "cn.wps.moffice_eng",
    "扫描全能王": "com.intsig.camscanner",
    
    # ========================================
    # 浏览器 (Browsers)
    # ========================================
    "Chrome": "com.android.chrome",
    "浏览器": "com.android.chrome",
    "Browser": "com.android.chrome",
    "夸克浏览器": "com.quark.browser",
    "QQ浏览器": "com.tencent.mtt",
    "UC浏览器": "com.UCMobile",
    "Edge": "com.microsoft.emmx",
    "Firefox": "org.mozilla.firefox",
    "Opera": "com.opera.browser",
    "Brave": "com.brave.browser",
    
    # ========================================
    # 工具类 (Tools & Utilities)
    # ========================================
    "Termux": "com.termux",
    "ToDesk": "youqu.android.todesk",
    "向日葵": "com.oray.sunlogin",
    
    # ========================================
    # AI助手 (AI Assistants)
    # ========================================
    "豆包": "com.larus.nova",
    "通义千问": "com.aliyun.tongyi",
    "讯飞星火": "com.iflytek.spark",
    "智谱清言": "com.zhipuai.qingyan",
    
    # ========================================
    # 云存储 (Cloud Storage)
    # ========================================
    "阿里云盘": "com.alicloud.databox",
    "百度网盘": "com.baidu.netdisk",
    "腾讯微云": "com.tencent.weiyun",
    "115网盘": "com.115.mobile",
    
    # ========================================
    # 金融银行 (Finance & Banking)
    # ========================================
    "云闪付": "com.unionpay",
    "工商银行": "com.icbc.im",
    "中国银行": "com.chinamworld.bocmbci",
    "农业银行": "com.android.bankabc",
    "建设银行": "com.ccb.mobile.csl",
    "招商银行": "cmb.pb",
    "交通银行": "com.bankcomm.Bankcomm",
    "邮储银行": "com.psbc.mbank",
    "中信银行": "com.citicbank.cibmb",
    "浦发银行": "com.spdb.mobilebank.per",
    "兴业银行": "com.yitong.mbank.psam",
    
    # ========================================
    # 政务服务 (Government & Public Services)
    # ========================================
    "国家反诈中心": "com.hicorenational.antifraud",
    "个人所得税": "cn.gov.tax.its",
    "医保服务平台": "cn.hsa.app",
    "交管12123": "com.tmri.app.main",
    "国家政务服务": "cn.gov.zwfw",
    
    # ========================================
    # 求职招聘 (Job & Career)
    # ========================================
    "Boss直聘": "com.hpbr.bosszhipin",
    "智联招聘": "com.zhaopin.social",
    "前程无忧": "com.51job.android",
    "猎聘": "com.liepin.android",
    "LinkedIn": "com.linkedin.android",
    
    # ========================================
    # 运营商 (Telecom)
    # ========================================
    "中国移动": "com.greenpoint.android.mc10086.activity",
    "中国联通": "com.sinovatech.unicom.ui",
    "中国电信": "com.ct.client",
    
    # ========================================
    # 教育学习 (Education)
    # ========================================
    "学习强国": "cn.xuexi.android",
    "中国大学MOOC": "com.netease.edu.ucmooc",
    "网易公开课": "com.netease.open",
    "知乎": "com.zhihu.android",
    "得到": "com.luojilab.player",
    "Coursera": "org.coursera.android",
    "Duolingo": "com.duolingo",
    "Khan Academy": "org.khanacademy.android",
    
    # ========================================
    # 社区论坛 (Community & Forums)
    # ========================================
    "Reddit": "com.reddit.frontpage",
    "Twitter": "com.twitter.android",
    "X": "com.twitter.android",  # Twitter更名为X
    "Facebook": "com.facebook.katana",
    
    # ========================================
    # 拍照摄影 (Photography)
    # ========================================
    "美颜相机": "com.meitu.beautyplusme",
    "美图秀秀": "com.mt.mtxx.mtxx",
    "Instagram": "com.instagram.android",
    "VSCO": "com.vsco.cam",
    "Snapseed": "com.niksoftware.snapseed",
    
    # ========================================
    # 输入法 (Input Methods)
    # ========================================
    "百度输入法": "com.baidu.input",
    "讯飞输入法": "com.iflytek.inputmethod",
    "搜狗输入法": "com.sohu.inputmethod.sogou",
    "QQ输入法": "com.tencent.qqinput",
    "Google拼音": "com.google.android.inputmethod.pinyin",
    
    # ========================================
    # Google服务 (Google Services)
    # ========================================
    "Gmail": "com.google.android.gm",
    "Google搜索": "com.google.android.googlequicksearchbox",
    "Google日历": "com.google.android.calendar",
    "Google相册": "com.google.android.apps.photos",
    "Google翻译": "com.google.android.apps.translate",
    "Google Keep": "com.google.android.keep",
    "Google Drive": "com.google.android.apps.docs",
    "Google Play": "com.android.vending",
    
    # ========================================
    # Microsoft服务 (Microsoft Services)
    # ========================================
    "Microsoft Authenticator": "com.azure.authenticator",
    "OneDrive": "com.microsoft.skydrive",
    "Outlook": "com.microsoft.office.outlook",
    "Word": "com.microsoft.office.word",
    "Excel": "com.microsoft.office.excel",
    "PowerPoint": "com.microsoft.office.powerpoint",
    
    # ========================================
    # 生活服务 (Life Services)
    # ========================================
    "淘票票": "com.taobao.movie.android",
    "猫眼": "com.sankuai.movie",
    "盒马": "com.wudaokou.hippo",  # 盒马鲜生
    "叮咚买菜": "com.yiduobuy.android",
}


def get_package_name(app_name: str) -> str | None:
    """
    根据应用名称获取包名（静态查询）
    
    注意: 此函数只查询静态字典，不支持别名、动态配置等高级功能。
    如需完整功能，请使用 AppConfigManager.find_app()

    Args:
        app_name: 应用显示名称（如"微信"）

    Returns:
        Android包名，未找到返回None
        
    示例:
        >>> get_package_name("微信")
        'com.tencent.mm'
    """
    return APP_PACKAGES.get(app_name)


def get_allowed_apps() -> list[str]:
    """
    获取允许操作的App列表（优先从动态配置读取）
    
    策略:
      1. 优先读取 data/app_config.json，返回启用的应用
      2. 如果配置文件不存在，返回所有静态应用（向后兼容）
    
    Returns:
        允许操作的App名称列表
        
    注意:
        此函数会读取文件，建议在启动时调用一次，或使用 AppConfigManager 缓存
    """
    import json
    import os
    
    config_file = "data/app_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 只返回启用的App
                return [app['display_name'] for app in data if app.get('enabled', False)]
        except Exception:
            pass
    
    # 默认返回所有已知App（向后兼容）
    return list(APP_PACKAGES.keys())


def get_app_name(package_name: str) -> str | None:
    """
    根据包名反查应用名称（静态查询）
    
    注意: 如果一个包名有多个别名（如"哔哩哔哩"/"bilibili"/"B站"），
         只会返回字典中第一个匹配的名称

    Args:
        package_name: Android包名

    Returns:
        应用显示名称，未找到返回None
        
    示例:
        >>> get_app_name("com.tencent.mm")
        '微信'
    """
    for name, package in APP_PACKAGES.items():
        if package == package_name:
            return name
    return None


def list_supported_apps() -> list[str]:
    """
    获取所有支持的应用名称列表（静态）
    
    Returns:
        所有内置应用的显示名称列表（100+个）
        
    注意:
        此函数返回所有静态应用，不考虑启用状态。
        如需获取启用的应用，请使用 get_allowed_apps()
    """
    return list(APP_PACKAGES.keys())
