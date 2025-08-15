// db.js - 更新为 SQLite 数据库连接

// 导入 sqlite3 库
// 使用 'sqlite3' 而不是 'mysql2/promise'
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';

// 定义数据库文件的路径
// 使用 path.resolve() 确保路径在任何操作系统上都能正确工作
// process.cwd() 返回 Node.js 进程的当前工作目录
const dbPath = path.resolve(process.cwd(), 'database.db');

let db;

// 异步函数来初始化和打开数据库连接
async function openDb() {
  // 如果数据库实例已存在，则直接返回
  if (db) {
    return db;
  }

  try {
    // 使用 `sqlite` 库的 `open` 函数来打开数据库文件
    db = await open({
      filename: dbPath,
      driver: sqlite3.Database
    });
    console.log('成功连接到 SQLite 数据库:', dbPath);
    return db;
  } catch (err) {
    console.error('打开数据库失败:', err);
    throw err;
  }
}

// 导出这个异步函数，以便在其他文件中使用
export { openDb };

// =============================================================
// API 路由处理器 - 适配 SQLite 的查询方式
// =============================================================

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: '方法不允许' });
  }

  try {
    const { query, params } = req.body;
    console.log('服务器收到查询:', query);
    console.log('服务器收到参数:', params);

    // 调用上面定义的函数来获取数据库连接
    const database = await openDb();

    try {
      // 使用 `db.all` 来执行查询并返回所有结果
      const results = await database.all(query, params);
      
      console.log('查询执行成功, 结果:', results);
      res.status(200).json({ results });
    } catch (dbError) {
      console.error('SQL执行错误:', {
        message: dbError.message,
        sql: query,
        values: params
      });

      // 返回更详细的错误信息
      res.status(500).json({
        error: dbError.message,
        sqlError: {
          sql: query,
          params: params
        }
      });
    }
  } catch (error) {
    console.error('服务器错误:', error);
    res.status(500).json({
      error: '服务器错误',
      details: error.message,
      stack: error.stack
    });
  }
}
