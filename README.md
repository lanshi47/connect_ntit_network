# 校园网络自动登录脚本

## 项目简介

这是一个使用Python和Selenium开发的自动化脚本,用于简化校园网络的登录过程。该脚本能够自动填写用户名和密码,选择网络服务提供商,并完成登录操作,大大提高了登录效率。

## 主要功能

- 自动打开登录页面
- 智能填写用户名和密码
- 自动选择网络服务提供商
- 执行登录操作
- 验证登录状态

## 技术栈

- Python 3.x
- Selenium WebDriver
- ChromeDriver

## 安装指南

1. 确保您的系统已安装Python 3.x
2. 安装所需的Python包:
   ```
   pip install selenium webdriver_manager
   ```
3. 下载与您的Chrome浏览器版本匹配的ChromeDriver

## 使用说明

1. 克隆或下载本项目到本地
2. 在`config.ini`文件中填写您的登录信息和网络设置
3. 运行脚本:
   ```
   python campus_network_login.py
   ```

## 开机自启动设置

为了使脚本在每次开机时自动运行，您可以创建一个BAT脚本并将其添加到Windows的启动文件夹中。以下是具体步骤：

1. **创建BAT脚本**:
   - 在任意文本编辑器中输入以下内容,如果采用虚拟环境,请自行调整shell指令：
     ```bat
      @echo off
      REM 设置控制台代码页为UTF-8，解决中文显示问题
      chcp 65001 >nul
      REM 切换到脚本目录
      cd /d E:\Users\Administrator\PycharmProjects\xxx
      
      REM 检查并创建配置文件
      if not exist "config.ini" (
          echo ini配置不存在
      )
      
      REM 设置权限
      icacls "config.ini" /grant Everyone:R /Q
      
      REM 运行Python脚本
      set PYTHONWARNINGS=ignore:SSL
      D:\ProgramData\anaconda3\envs\xxx\python.exe -W ignore connect_school_network.py 2>nul
      
      if errorlevel 1 (
          echo 运行失败，错误代码：%errorlevel%
          echo 详细信息请查看日志文件
          timeout /t 10
          exit /b %errorlevel%
      )
      echo 运行成功
      timeout /t 5
     ```
   - 将文件保存为`start_login.bat`（确保文件类型选择为“所有文件”）。

2. **将BAT脚本添加到启动文件夹**:
   - 按下 `Win + R` 键，输入 `shell:startup`，然后按回车。这将打开Windows的启动文件夹。
   - 将刚刚创建的`start_login.bat`文件复制到此文件夹中。

3. **测试开机自启动**:
   - 重启计算机，确认脚本是否在开机后自动运行。

## 配置文件说明

在`config.ini`文件中,您需要设置以下信息:

- `USERNAME`: 您的校园网账号
- `PASSWORD`: 您的登录密码
- `PROVIDER`: 网络服务提供商名称
- `LOGIN_URL`: 登录页面的URL

## 注意事项

- 请确保您的网络连接稳定
- 定期更新ChromeDriver以匹配您的Chrome浏览器版本
- 不要将包含敏感信息的配置文件分享给他人

## 常见问题

1. Q: 脚本运行时报错"ElementNotInteractableException"
   A: 这通常是因为页面元素还未完全加载。尝试增加等待时间或使用显式等待。

2. Q: 无法选择正确的网络服务提供商
   A: 检查`config.ini`中的`PROVIDER`设置是否与页面上显示的完全一致。

## 贡献指南

欢迎提交问题报告和改进建议。如果您想为项目做出贡献,请遵循以下步骤:

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 将您的更改推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情


## 贡献指南

欢迎提交问题报告和改进建议。如果您想为项目做出贡献,请遵循以下步骤:

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 将您的更改推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request



感谢您使用校园网络自动登录脚本!


