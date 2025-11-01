#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClassMint 默认账号查看工具
用于查看系统自动创建的默认账号信息
"""

import sqlite3
import sys
import os

def get_default_accounts():
    """获取默认账号信息"""
    db_path = "classmint.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，请先运行 Flask 应用初始化数据库")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("ClassMint 默认账号信息")
        print("=" * 50)
        
        # 获取教师账号
        teacher = cursor.execute("SELECT username FROM users WHERE username = 'admin'").fetchone()
        if teacher:
            print("教师账号:")
            print("   用户名: admin")
            print("   密码: admin123")
            print("   说明: 首次运行系统时自动创建")
            print()
        
        # 获取学生账号
        students = cursor.execute("SELECT username FROM users WHERE username LIKE 'student%' ORDER BY username").fetchall()
        if students:
            print("学生账号:")
            for student in students:
                print(f"   用户名: {student['username']}")
                print("   密码: student123")
            print("   说明: 首次运行系统时自动创建")
            print()
        
        # 获取商品信息
        items = cursor.execute("SELECT COUNT(*) as count FROM shop_items WHERE status = 'ACTIVE'").fetchone()
        if items and items['count'] > 0:
            print("商店商品:")
            print(f"   已创建 {items['count']} 个默认商品")
            print("   包括: 苹果、书籍、礼品卡、咖啡、游戏时间、奖杯")
            print()
        
        print("安全提示:")
        print("   1. 建议首次登录后立即修改密码")
        print("   2. 生产环境中应删除这些默认账号")
        print("   3. 使用强密码并定期更换")
        
    except Exception as e:
        print(f"读取数据库时出错: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    get_default_accounts()
