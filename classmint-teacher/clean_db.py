#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClassMint 数据库清理工具
清理历史脏数据，保留基础配置数据
"""

import sqlite3
import sys
import os
import shutil
from datetime import datetime

def clean_database():
    """清理数据库中的脏数据"""
    db_path = "classmint.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，请先运行 Flask 应用初始化数据库")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("ClassMint 数据库清理工具")
        print("=" * 50)
        
        # 显示清理前的数据统计
        print("清理前的数据统计:")
        
        tokens_count = cursor.execute("SELECT COUNT(*) as count FROM tokens").fetchone()["count"]
        claims_count = cursor.execute("SELECT COUNT(*) as count FROM claims").fetchone()["count"]
        ledger_count = cursor.execute("SELECT COUNT(*) as count FROM ledger").fetchone()["count"]
        balances_count = cursor.execute("SELECT COUNT(*) as count FROM user_balances").fetchone()["count"]
        purchases_count = cursor.execute("SELECT COUNT(*) as count FROM purchases").fetchone()["count"]
        
        print(f"   令牌记录: {tokens_count}")
        print(f"   领取记录: {claims_count}")
        print(f"   区块链记录: {ledger_count}")
        print(f"   用户余额: {balances_count}")
        print(f"   购买记录: {purchases_count}")
        print()
        
        print("即将清理以下表的数据:")
        print("   - tokens (令牌记录)")
        print("   - claims (领取记录)")
        print("   - ledger (区块链记录)")
        print("   - user_balances (用户余额)")
        print("   - purchases (购买记录)")
        print()
        print("将保留以下表的数据:")
        print("   - users (用户账号)")
        print("   - shop_items (商店商品)")
        print()
        
        # 开始清理
        print("开始清理数据...")
        
        # 清理交易相关表
        cursor.execute("DELETE FROM purchases")
        print("   已清理购买记录")
        
        cursor.execute("DELETE FROM user_balances")
        print("   已清理用户余额")
        
        cursor.execute("DELETE FROM ledger")
        print("   已清理区块链记录")
        
        cursor.execute("DELETE FROM claims")
        print("   已清理领取记录")
        
        cursor.execute("DELETE FROM tokens")
        print("   已清理令牌记录")
        
        # 重置自增ID
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('tokens', 'claims', 'ledger', 'user_balances', 'purchases')")
        print("   已重置自增ID")
        
        # 重新初始化学生余额
        current_time = int(datetime.now().timestamp())
        cursor.execute("INSERT OR IGNORE INTO user_balances (user_id, balance, updated_at) VALUES (2, 0, ?)", (current_time,))
        cursor.execute("INSERT OR IGNORE INTO user_balances (user_id, balance, updated_at) VALUES (3, 0, ?)", (current_time,))
        cursor.execute("INSERT OR IGNORE INTO user_balances (user_id, balance, updated_at) VALUES (4, 0, ?)", (current_time,))
        print("   已重新初始化学生余额")
        
        # 提交更改
        conn.commit()
        
        # 显示清理后的数据统计
        print()
        print("清理后的数据统计:")
        
        tokens_count = cursor.execute("SELECT COUNT(*) as count FROM tokens").fetchone()["count"]
        claims_count = cursor.execute("SELECT COUNT(*) as count FROM claims").fetchone()["count"]
        ledger_count = cursor.execute("SELECT COUNT(*) as count FROM ledger").fetchone()["count"]
        balances_count = cursor.execute("SELECT COUNT(*) as count FROM user_balances").fetchone()["count"]
        purchases_count = cursor.execute("SELECT COUNT(*) as count FROM purchases").fetchone()["count"]
        users_count = cursor.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        items_count = cursor.execute("SELECT COUNT(*) as count FROM shop_items").fetchone()["count"]
        
        print(f"   令牌记录: {tokens_count}")
        print(f"   领取记录: {claims_count}")
        print(f"   区块链记录: {ledger_count}")
        print(f"   用户余额: {balances_count}")
        print(f"   购买记录: {purchases_count}")
        print(f"   用户账号: {users_count}")
        print(f"   商店商品: {items_count}")
        
        print()
        print("数据库清理完成!")
        print("现在可以重新开始使用系统，所有交易记录都是干净的")
        
        return True
        
    except Exception as e:
        print(f"清理过程中出错: {e}")
        return False
    finally:
        conn.close()

def backup_database():
    """备份数据库"""
    db_path = "classmint.db"
    backup_path = f"classmint_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return False
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"数据库已备份到: {backup_path}")
        return True
    except Exception as e:
        print(f"备份失败: {e}")
        return False

if __name__ == "__main__":
    # 先备份再清理
    print("正在备份数据库...")
    if backup_database():
        clean_database()
    else:
        print("备份失败，取消清理操作")
