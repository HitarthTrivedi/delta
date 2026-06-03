// ============================================================
// Efferd-Style Dashboard Component
// Tech Stack: React 19 + Tailwind CSS v4 + shadcn/ui patterns
// ============================================================

// --- Dependencies needed ---
// npm install lucide-react recharts clsx tailwind-merge
// npx shadcn@latest add card badge button avatar dropdown-menu

import React, { useState } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  LayoutDashboard,
  Users,
  ShoppingCart,
  TrendingUp,
  DollarSign,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Bell,
  Search,
  Menu,
  ChevronDown,
  CreditCard,
  Package,
  Calendar,
  MoreHorizontal,
} from "lucide-react";

// --- Mock Data ---
const revenueData = [
  { name: "Jan", revenue: 4200, profit: 2400 },
  { name: "Feb", revenue: 5100, profit: 3100 },
  { name: "Mar", revenue: 4800, profit: 2800 },
  { name: "Apr", revenue: 6200, profit: 3900 },
  { name: "May", revenue: 7100, profit: 4500 },
  { name: "Jun", revenue: 6800, profit: 4200 },
  { name: "Jul", revenue: 8100, profit: 5300 },
];

const trafficData = [
  { name: "Mon", visitors: 1200, pageViews: 3400 },
  { name: "Tue", visitors: 1900, pageViews: 4200 },
  { name: "Wed", visitors: 1600, pageViews: 3800 },
  { name: "Thu", visitors: 2100, pageViews: 5100 },
  { name: "Fri", visitors: 2400, pageViews: 5800 },
  { name: "Sat", visitors: 1800, pageViews: 4100 },
  { name: "Sun", visitors: 1500, pageViews: 3600 },
];

const categoryData = [
  { name: "Electronics", value: 35, color: "#3b82f6" },
  { name: "Clothing", value: 25, color: "#8b5cf6" },
  { name: "Home", value: 20, color: "#10b981" },
  { name: "Sports", value: 15, color: "#f59e0b" },
  { name: "Books", value: 5, color: "#ef4444" },
];

const recentOrders = [
  { id: "#ORD-7523", customer: "Alex Morgan", product: "Wireless Headphones", amount: "$129.00", status: "completed", date: "2 min ago" },
  { id: "#ORD-7522", customer: "Sarah Chen", product: "Smart Watch Gen 5", amount: "$299.00", status: "processing", date: "15 min ago" },
  { id: "#ORD-7521", customer: "James Wilson", product: "Mechanical Keyboard", amount: "$149.00", status: "completed", date: "1 hr ago" },
  { id: "#ORD-7520", customer: "Emily Davis", product: "USB-C Hub", amount: "$59.00", status: "pending", date: "2 hrs ago" },
  { id: "#ORD-7519", customer: "Michael Brown", product: "4K Monitor", amount: "$449.00", status: "completed", date: "3 hrs ago" },
];

// --- Components ---

const Card = ({ children, className = "" }) => (
  <div className={`bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm ${className}`}>
    {children}
  </div>
);

const Badge = ({ children, variant = "default" }) => {
  const styles = {
    default: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
    success: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    warning: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    danger: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    processing: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[variant] || styles.default}`}>
      {children}
    </span>
  );
};

const KPICard = ({ title, value, change, changeType, icon: Icon, trend }) => (
  <Card className="p-6 hover:shadow-md transition-shadow duration-200">
    <div className="flex items-start justify-between">
      <div className="space-y-2">
        <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</p>
        <h3 className="text-2xl font-bold text-zinc-900 dark:text-white">{value}</h3>
        <div className="flex items-center gap-1">
          {changeType === "up" ? (
            <ArrowUpRight className="w-4 h-4 text-emerald-500" />
          ) : (
            <ArrowDownRight className="w-4 h-4 text-red-500" />
          )}
          <span className={`text-sm font-medium ${changeType === "up" ? "text-emerald-600" : "text-red-600"}`}>
            {change}
          </span>
          <span className="text-sm text-zinc-400">vs last month</span>
        </div>
      </div>
      <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
        <Icon className="w-5 h-5 text-zinc-600 dark:text-zinc-400" />
      </div>
    </div>
  </Card>
);

const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
      active
        ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
        : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
    }`}
  >
    <Icon className="w-5 h-5" />
    {label}
  </button>
);

// --- Main Dashboard ---
export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [timeRange, setTimeRange] = useState("7d");

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "analytics", label: "Analytics", icon: TrendingUp },
    { id: "orders", label: "Orders", icon: ShoppingCart },
    { id: "customers", label: "Customers", icon: Users },
    { id: "products", label: "Products", icon: Package },
  ];

  const getStatusBadge = (status) => {
    const map = {
      completed: <Badge variant="success">Completed</Badge>,
      processing: <Badge variant="processing">Processing</Badge>,
      pending: <Badge variant="warning">Pending</Badge>,
    };
    return map[status] || <Badge>{status}</Badge>;
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans">
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 transition-all duration-300 z-40 ${
          sidebarOpen ? "w-64" : "w-0 overflow-hidden"
        }`}
      >
        <div className="p-6">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 dark:bg-white flex items-center justify-center">
              <Activity className="w-5 h-5 text-white dark:text-zinc-900" />
            </div>
            <span className="text-lg font-bold tracking-tight">Efferd</span>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => (
              <SidebarItem
                key={item.id}
                icon={item.icon}
                label={item.label}
                active={activeTab === item.id}
                onClick={() => setActiveTab(item.id)}
              />
            ))}
          </nav>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-sm font-medium">
              JD
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">John Doe</p>
              <p className="text-xs text-zinc-500 truncate">john@example.com</p>
            </div>
            <ChevronDown className="w-4 h-4 text-zinc-400" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`transition-all duration-300 ${sidebarOpen ? "ml-64" : "ml-0"}`}>
        {/* Header */}
        <header className="sticky top-0 z-30 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="pl-10 pr-4 py-2 w-64 rounded-lg bg-zinc-100 dark:bg-zinc-800 border-0 text-sm focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white outline-none"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex bg-zinc-100 dark:bg-zinc-800 rounded-lg p-1">
                {["24h", "7d", "30d", "90d"].map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      timeRange === range
                        ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm"
                        : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
              <button className="relative p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="p-6 max-w-7xl mx-auto space-y-6">
          {/* Page Header */}
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                Welcome back! Here's what's happening with your store.
              </p>
            </div>
            <button className="px-4 py-2 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity">
              Download Report
            </button>
          </div>

          {/* KPI Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Total Revenue"
              value="$48,294"
              change="12.5%"
              changeType="up"
              icon={DollarSign}
            />
            <KPICard
              title="Total Orders"
              value="1,429"
              change="8.2%"
              changeType="up"
              icon={ShoppingCart}
            />
            <KPICard
              title="Active Customers"
              value="3,642"
              change="2.1%"
              changeType="down"
              icon={Users}
            />
            <KPICard
              title="Conversion Rate"
              value="3.24%"
              change="0.8%"
              changeType="up"
              icon={TrendingUp}
            />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Revenue Chart */}
            <Card className="lg:col-span-2 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-semibold">Revenue Overview</h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">Monthly revenue and profit trends</p>
                </div>
                <button className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg">
                  <MoreHorizontal className="w-4 h-4 text-zinc-400" />
                </button>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={revenueData}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#18181b",
                      border: "none",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2} fill="url(#colorRevenue)" />
                  <Area type="monotone" dataKey="profit" stroke="#10b981" strokeWidth={2} fill="url(#colorProfit)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            {/* Category Distribution */}
            <Card className="p-6">
              <div className="mb-6">
                <h3 className="text-base font-semibold">Sales by Category</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Product category breakdown</p>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-4">
                {categoryData.map((cat) => (
                  <div key={cat.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                      <span className="text-zinc-600 dark:text-zinc-400">{cat.name}</span>
                    </div>
                    <span className="font-medium">{cat.value}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Bottom Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Traffic Chart */}
            <Card className="p-6">
              <div className="mb-6">
                <h3 className="text-base font-semibold">Website Traffic</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Daily visitors and page views</p>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={trafficData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#18181b",
                      border: "none",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                    cursor={{ fill: "#f4f4f5" }}
                  />
                  <Bar dataKey="visitors" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="pageViews" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            {/* Recent Orders */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-base font-semibold">Recent Orders</h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">Latest transactions</p>
                </div>
                <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">View All</button>
              </div>
              <div className="space-y-3">
                {recentOrders.map((order) => (
                  <div
                    key={order.id}
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                        <Package className="w-4 h-4 text-zinc-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{order.product}</p>
                        <p className="text-xs text-zinc-500">{order.customer} · {order.id}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{order.amount}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {getStatusBadge(order.status)}
                        <span className="text-xs text-zinc-400">{order.date}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}