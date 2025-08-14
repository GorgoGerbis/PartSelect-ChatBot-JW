#!/usr/bin/env python3
"""
Quick PostgreSQL connection test to debug the issue
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test different PostgreSQL connection scenarios"""
    
    print("=== PostgreSQL Connection Test ===")
    
    # show what were trying to connect with
    print(f"PG_DB_HOST {os.getenv('PG_DB_HOST')}")
    print(f"PG_DB_USER {os.getenv('PG_DB_USER')}")
    print(f"PG_DB_NAME {os.getenv('PG_DB_NAME')}")
    print(f"PG_DB_PASSWORD {'*' * len(os.getenv('PG_DB_PASSWORD', ''))}")
    print()
    
    # test 1 try with your configured settings
    print("Test 1 Your configured settings")
    try:
        host = os.getenv('PG_DB_HOST', 'localhost')
        user = os.getenv('PG_DB_USER', 'partselect_user')
        password = os.getenv('PG_DB_PASSWORD', 'your_secure_db_password')
        database = os.getenv('PG_DB_NAME', 'partselect_db')
        
        conn = await asyncpg.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=5432
        )
        print("SUCCESS Connected with your settings")
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL version {version}")
        await conn.close()
        return True
        
    except Exception as e:
        print(f"FAILED {e}")
        print()
    
    # test 2 try with default postgres user and postgres database
    print("Test 2 Default postgres user")
    try:
        conn = await asyncpg.connect(
            host='localhost',
            user='postgres',
            password='your_secure_db_password',  # try same password
            database='postgres',  # default database
            port=5432
        )
        print("SUCCESS Connected with postgres user")
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL version {version}")
        await conn.close()
        return True
        
    except Exception as e:
        print(f"FAILED {e}")
        print()
    
    # test 3 try different common passwords
    print("Test 3 Trying common passwords with postgres user")
    common_passwords = ['postgres', 'password', 'admin', '123456', '']
    
    for pwd in common_passwords:
        try:
            conn = await asyncpg.connect(
                host='localhost',
                user='postgres',
                password=pwd,
                database='postgres',
                port=5432
            )
            print(f"SUCCESS Connected with postgres user and password '{pwd}'")
            version = await conn.fetchval("SELECT version()")
            print(f"PostgreSQL version {version}")
            await conn.close()
            return True
            
        except Exception as e:
            print(f"Password '{pwd}' failed {e}")
    
    print("\nAll connection attempts failed")
    print("Please check")
    print("1 Is PostgreSQL running netstat shows it is")
    print("2 What username password did you set when installing PostgreSQL")
    print("3 Try connecting with DBeaver to confirm credentials")
    return False

if __name__ == "__main__":
    asyncio.run(test_connection())
