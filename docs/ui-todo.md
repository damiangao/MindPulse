# UI Improvements Todo

## 1. Sidebar Header Design
**问题：** 左上角的用户 email 和 logout 按钮隐藏设计，很难看

**现状：**
```jsx
<div className="flex items-center justify-between p-4 border-b">
  <span className="font-medium truncate">{user.email}</span>
  <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">Logout</button>
</div>
```

**TODO:**
- [ ] 重新设计 sidebar header：用户信息应该更突出
- [ ] 考虑把 logout 按钮放到更明显的位置（比如和 New Chat 并排）
- [ ] 或者用下拉菜单/头像方式展示用户

## 2. 输入框上移后底部空出来
**问题：** 消息区域滚动后（隐藏上方内容），输入框会往上移一大截，导致输入框下面空出来一块

**现状：**
- ChatWindow 使用 `flex-1 flex flex-col`
- messages 区域用 `flex-1 overflow-y-auto`
- 输入框固定在底部 `border-t`

**TODO:**
- [ ] 检查 flexbox 布局是否正确
- [ ] 确保输入框始终贴底
- [ ] 修复底部空白问题

## 3. 整体布局检查
**TODO:**
- [ ] 检查 ChatWindow 的 flex 布局
- [ ] 确保 messages 区域正确填充剩余空间
- [ ] 输入框始终在视口底部

---

## 优先级

1. **P0 - 输入框布局问题**（影响使用）
2. **P1 - Sidebar header 设计**（影响美观）

---

## 建议设计方案

### Sidebar Header
```
方案A: 把用户信息放到 sidebar 底部（和 New Chat 分开）
方案B: 用 Avatar + 下拉菜单形式，更现代
方案C: 用户信息放到主区域 header，sidebar 只保留 chat list
```

### 输入框布局
```
确保 flex 布局正确：
<div className="flex-1 flex flex-col">
  <div className="flex-1 overflow-y-auto">messages</div>
  <div className="shrink-0">input</div>  ← 确保 input 不会被压缩
</div>
```