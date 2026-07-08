"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast, Toaster } from "sonner";
import { apiClient, getApiError } from "../api-client";
import {
  FaUtensils,
  FaWallet,
  FaPlus,
  FaCamera,
  FaBarcode,
  FaSearch,
  FaUserFriends,
  FaBell,
  FaSignOutAlt,
  FaCheck,
  FaTimes,
  FaExclamationTriangle,
  FaCoins,
  FaFire,
  FaCreditCard,
  FaChevronLeft,
  FaCog,
  FaUser,
  FaBars,
  FaLock,
  FaTrash,
  FaMoon,
  FaSun,
} from "react-icons/fa";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type ActiveModule = "hub" | "calorie" | "budget";

export default function Dashboard() {
  const router = useRouter();
  const [activeModule, setActiveModule] = useState<ActiveModule>("hub");
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  
  // Customization States
  const [currency, setCurrency] = useState<"INR" | "USD">("INR"); // Currency state
  const [greeting, setGreeting] = useState("Welcome back");
  const [scanPulse, setScanPulse] = useState(false);
  const [isLightMode, setIsLightMode] = useState(false); // Theme mode state

  // Calorie Tracker States
  const [calorieData, setCalorieData] = useState<any>({
    target_calories: 2000,
    consumed_calories: 0,
    remaining_calories: 2000,
    target_protein: 150,
    consumed_protein: 0,
    target_carbs: 225,
    consumed_carbs: 0,
    target_fat: 65,
    consumed_fat: 0,
    logs: [],
    history_7_days: [],
  });

  const [foodDesc, setFoodDesc] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [scanQueue, setScanQueue] = useState<any[]>([]);
  const [scanQtys, setScanQtys] = useState<Record<string, number>>({});
  const [barcodeInput, setBarcodeInput] = useState("");

  // Budget Planner States
  const [budgetData, setBudgetData] = useState<any>({
    monthly_total: 0,
    income_total: 0,
    expense_total: 0,
    personal_total: 0,
    collaborative_total: 0,
    transactions: [],
    collaborations: [],
    notifications: [],
  });

  const [bgAmount, setBgAmount] = useState("");
  const [bgReason, setBgReason] = useState("");
  const [bgCategory, setBgCategory] = useState("Food");
  const [bgDate, setBgDate] = useState(new Date().toISOString().split("T")[0]);
  const [bgCollaborative, setBgCollaborative] = useState(false);
  const [bgCollabId, setBgCollabId] = useState("");

  const [partnerInput, setPartnerInput] = useState("");
  const [collabNameInput, setCollabNameInput] = useState("Shared Budget");

  const [showNotifications, setShowNotifications] = useState(false);

  // Profile Edit Modal States
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [editWeight, setEditWeight] = useState("");
  const [editGoalWeight, setEditGoalWeight] = useState("");
  const [editHeight, setEditHeight] = useState("");
  const [editGoal, setEditGoal] = useState("lose");
  const [editActivity, setEditActivity] = useState("sedentary");
  const [editExerciseDays, setEditExerciseDays] = useState(3);
  const [editFullName, setEditFullName] = useState("");
  const [editSex, setEditSex] = useState("male");
  const [editDob, setEditDob] = useState("");

  // Hamburger Drawer and Sub-modal States
  const [showAppMenu, setShowAppMenu] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState("");

  // Helper Currency Symbol Getter
  const getCurrencySymbol = () => {
    return currency === "INR" ? "₹" : "$";
  };

  // Calculate age helper
  const calculateAge = (dobString: string) => {
    if (!dobString) return 0;
    const today = new Date();
    const birthDate = new Date(dobString);
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  // Determine dynamic greeting based on system time
  useEffect(() => {
    const hrs = new Date().getHours();
    if (hrs < 12) setGreeting("Good morning");
    else if (hrs < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");
  }, []);

  // Fetch all initial data
  const fetchData = async () => {
    try {
      const profRes = await apiClient.get("/profile/me");
      setProfile(profRes.data);
      
      // Seed profile edit values
      setEditWeight(profRes.data.current_weight_kg.toString());
      setEditGoalWeight(profRes.data.goal_weight_kg.toString());
      setEditHeight(profRes.data.height_cm.toString());
      setEditGoal(profRes.data.goal);
      setEditActivity(profRes.data.activity_level);
      setEditExerciseDays(profRes.data.exercise_days_per_week);
      setEditFullName(profRes.data.full_name);
      setEditSex(profRes.data.sex);
      setEditDob(profRes.data.date_of_birth);

      const calRes = await apiClient.get("/calorie/dashboard");
      setCalorieData(calRes.data);

      const budRes = await apiClient.get("/budget/dashboard");
      setBudgetData(budRes.data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        toast.error("Session expired. Please login again.");
        router.push("/");
      } else {
        toast.error("Please configure your profile setup first.");
        router.push("/profile-setup");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    toast.success("Logged out successfully.");
    router.push("/");
  };

  // --- Profile Edit Submission Handler ---
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiClient.patch("/profile", {
        height_cm: parseFloat(editHeight),
        current_weight_kg: parseFloat(editWeight),
        goal_weight_kg: parseFloat(editGoalWeight),
        goal: editGoal,
        activity_level: editActivity,
        exercise_days_per_week: editExerciseDays,
      });
      setProfile(res.data);
      toast.success("Physical fitness parameters updated!");
      setShowProfileModal(false);
      
      // Refresh calculations
      const calRes = await apiClient.get("/calorie/dashboard");
      setCalorieData(calRes.data);
    } catch (err) {
      toast.error("Failed to update profile data.");
    } finally {
      setLoading(false);
    }
  };

  // --- Change Password Handler ---
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) return;
    setLoading(true);
    try {
      await apiClient.patch("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success("Password changed successfully!");
      setShowPasswordModal(false);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  // --- Delete Account Handler ---
  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deleteConfirmationText.toLowerCase() !== "delete my account") {
      toast.error("Please enter the exact confirmation text.");
      return;
    }
    setLoading(true);
    try {
      await apiClient.delete("/auth/account");
      toast.success("Account permanently deleted. All session history wiped.");
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      router.push("/");
    } catch (err) {
      toast.error("Failed to delete account. Try again later.");
    } finally {
      setLoading(false);
    }
  };

  // --- Calorie Log Handlers ---
  const handleParseFood = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!foodDesc.trim()) return;
    setScanPulse(true);
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      const res = await apiClient.post("/calorie/parse", { description: foodDesc });
      const id = `scan-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const newItem = { ...res.data, _id: id, _source: "text", _time: new Date().toLocaleTimeString() };
      setScanQueue((prev) => [...prev, newItem]);
      setScanQtys((prev) => ({ ...prev, [id]: 1 }));
      setFoodDesc("");
      toast.success("Meal description parsed!");
    } catch (err) {
      toast.error("Failed to parse food description.");
    } finally {
      setScanPulse(false);
      setLoading(false);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setImageFile(file);
    setScanPulse(true);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await new Promise((resolve) => setTimeout(resolve, 1200));
      const res = await apiClient.post("/calorie/scan-image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const id = `scan-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const newItem = { ...res.data, _id: id, _source: "image", _filename: file.name, _time: new Date().toLocaleTimeString() };
      setScanQueue((prev) => [...prev, newItem]);
      setScanQtys((prev) => ({ ...prev, [id]: 1 }));
      setImageFile(null);
      toast.success("AI scanning finished!");
    } catch (err) {
      toast.error("Failed to scan image.");
    } finally {
      setScanPulse(false);
      setLoading(false);
      // Reset input so same file can be selected again
      e.target.value = "";
    }
  };

  const handleBarcodeLookup = async (barcode: string) => {
    if (!barcode) return;
    setScanPulse(true);
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 600));
      const res = await apiClient.get(`/calorie/barcode/${barcode}`);
      const id = `scan-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const newItem = { ...res.data, _id: id, _source: "barcode", _time: new Date().toLocaleTimeString() };
      setScanQueue((prev) => [...prev, newItem]);
      setScanQtys((prev) => ({ ...prev, [id]: 1 }));
      setBarcodeInput("");
      toast.success("EAN barcode matched!");
    } catch (err) {
      toast.error("Barcode not recognized in Open Food Facts database.");
    } finally {
      setScanPulse(false);
      setLoading(false);
    }
  };

  const submitScanItem = async (item: any) => {
    const qty = scanQtys[item._id] ?? 1;
    setLoading(true);
    try {
      await apiClient.post("/calorie/log", {
        food_name: item.food_name,
        calories: Math.round(item.calories * qty),
        protein: parseFloat((item.protein * qty).toFixed(1)),
        carbs: parseFloat((item.carbs * qty).toFixed(1)),
        fat: parseFloat((item.fat * qty).toFixed(1)),
        logged_date: new Date().toISOString().split("T")[0],
      });
      toast.success(`${item.food_name} logged!`);
      // Remove only this item from the queue
      setScanQueue((prev) => prev.filter((i) => i._id !== item._id));
      setScanQtys((prev) => { const n = { ...prev }; delete n[item._id]; return n; });
      const calRes = await apiClient.get("/calorie/dashboard");
      setCalorieData(calRes.data);
    } catch (err) {
      toast.error("Failed to save calorie log.");
    } finally {
      setLoading(false);
    }
  };

  const updateQueueItem = (id: string, field: string, value: any) => {
    setScanQueue((prev) => prev.map((item) => item._id === id ? { ...item, [field]: value } : item));
  };

  const dismissScanItem = (id: string) => {
    setScanQueue((prev) => prev.filter((i) => i._id !== id));
    setScanQtys((prev) => { const n = { ...prev }; delete n[id]; return n; });
  };

  // --- Budget Log Handlers ---
  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bgAmount || !bgReason) {
      toast.error("Fill in all transaction fields.");
      return;
    }
    setLoading(true);
    try {
      await apiClient.post("/budget/transaction", {
        amount: parseFloat(bgAmount),
        reason: bgReason,
        category: bgCategory,
        date: bgDate,
        is_collaborative: bgCollaborative,
        collaboration_id: bgCollaborative && bgCollabId ? bgCollabId : null,
      });
      toast.success("Transaction recorded!");
      setBgAmount("");
      setBgReason("");
      
      const budRes = await apiClient.get("/budget/dashboard");
      setBudgetData(budRes.data);
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!partnerInput) return;
    setLoading(true);
    try {
      await apiClient.post("/budget/invite", {
        partner_email_or_phone: partnerInput,
        name: collabNameInput,
      });
      toast.success("Collaboration invitation sent!");
      setPartnerInput("");
      
      const budRes = await apiClient.get("/budget/dashboard");
      setBudgetData(budRes.data);
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleInviteResponse = async (collabId: string, status: "accepted" | "rejected") => {
    setLoading(true);
    try {
      await apiClient.post(`/budget/invite/${collabId}/respond`, { status });
      toast.success(`Invitation ${status}!`);
      
      const budRes = await apiClient.get("/budget/dashboard");
      setBudgetData(budRes.data);
    } catch (err) {
      toast.error("Failed to respond to invitation.");
    } finally {
      setLoading(false);
    }
  };

  const handleClearNotifications = async () => {
    try {
      await apiClient.post("/budget/notifications/read");
      const budRes = await apiClient.get("/budget/dashboard");
      setBudgetData(budRes.data);
      toast.success("Notifications marked as read.");
    } catch (err) {
      toast.error("Failed to clear notifications.");
    }
  };

  // Helper macro calculations
  const pPct = Math.min(100, Math.round((calorieData.consumed_protein / (calorieData.target_protein || 1)) * 100));
  const cPct = Math.min(100, Math.round((calorieData.consumed_carbs / (calorieData.target_carbs || 1)) * 100));
  const fPct = Math.min(100, Math.round((calorieData.consumed_fat / (calorieData.target_fat || 1)) * 100));
  const calPct = Math.min(100, Math.round((calorieData.consumed_calories / (calorieData.target_calories || 1)) * 100));

  const unreadNotifications = budgetData.notifications.filter((n: any) => !n.is_read);

  // Compute category breakdown stats for Budget
  const categoryTotals: Record<string, number> = {};
  budgetData.transactions.forEach((t: any) => {
    categoryTotals[t.category] = (categoryTotals[t.category] || 0) + t.amount;
  });
  const maxCategoryTotal = Math.max(...Object.values(categoryTotals), 1);

  if (loading && !profile) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-400 font-sans">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <span>Synchronizing NutriBudget AI dashboards...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen font-sans pb-16 relative overflow-x-hidden transition-colors duration-300 ${
      isLightMode ? "bg-zinc-50 text-zinc-900" : "bg-zinc-950 text-zinc-100"
    }`}>
      <Toaster position="top-right" theme={isLightMode ? "light" : "dark"} />

      {/* Background blurs */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-emerald-500/5 rounded-full blur-[180px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[180px] pointer-events-none" />

      {/* Main navigation header */}
      <header className={`border-b sticky top-0 z-45 backdrop-blur-md transition-colors ${
        isLightMode ? "border-zinc-200 bg-white/60" : "border-zinc-900 bg-zinc-900/30"
      }`}>
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
          
          <div className="flex items-center gap-3 shrink-0">
            {activeModule !== "hub" && (
              <button
                onClick={() => {
                  setActiveModule("hub");
                }}
                className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-xl transition-all duration-300 hover:scale-105 active:scale-95 ${
                  isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-700 hover:bg-zinc-200" : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <FaChevronLeft className="text-[10px]" /> Hub
              </button>
            )}
            <span className="text-lg font-black bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent transition-all duration-300 hover:brightness-110">
              NutriBudget AI
            </span>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-305 active:scale-90 relative ${
                  isLightMode ? "border-zinc-250 bg-zinc-100 hover:bg-zinc-200 text-zinc-700" : "border-zinc-800 bg-zinc-950/40 hover:bg-zinc-850 text-zinc-400"
                }`}
              >
                <FaBell className="text-xs" />
                {unreadNotifications.length > 0 && (
                  <span className="absolute top-0.5 right-0.5 bg-red-500 text-white rounded-full text-[8px] w-3.5 h-3.5 flex items-center justify-center font-bold animate-pulse">
                    {unreadNotifications.length}
                  </span>
                )}
              </button>

              {/* Notification Drawer */}
              {showNotifications && (
                <div className={`absolute right-0 mt-3 w-80 border rounded-2xl shadow-2xl p-4 z-50 max-h-96 overflow-y-auto animate-fade-in ${
                  isLightMode ? "bg-white border-zinc-200 text-zinc-800" : "bg-zinc-900 border-zinc-800 text-zinc-200"
                }`}>
                  <div className={`flex items-center justify-between border-b pb-2 mb-3 ${
                    isLightMode ? "border-zinc-100" : "border-zinc-800"
                  }`}>
                    <span className="text-xs font-bold">Shared Activity Logs</span>
                    {unreadNotifications.length > 0 && (
                      <button
                        onClick={handleClearNotifications}
                        className="text-[10px] text-emerald-500 hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  {budgetData.notifications.length === 0 ? (
                    <div className="text-center py-6 text-xs text-zinc-500">No new notifications.</div>
                  ) : (
                    <div className="space-y-3">
                      {budgetData.notifications.map((n: any) => (
                        <div
                          key={n.id}
                          className={`p-2.5 rounded-xl border text-xs leading-relaxed transition-all ${
                            n.is_read
                              ? (isLightMode ? "bg-zinc-50 border-zinc-100 text-zinc-450" : "bg-zinc-950/30 border-zinc-900 text-zinc-500")
                              : (isLightMode ? "bg-emerald-50/50 border-emerald-100 text-zinc-800 font-medium" : "bg-zinc-950/80 border-emerald-500/20 text-zinc-200 font-medium")
                          }`}
                        >
                          {n.message}
                          <span className="block text-[9px] text-zinc-555 mt-1">
                            {new Date(n.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Hamburger 3-Line Menu Trigger */}
            <div className="pl-3 border-l border-zinc-850">
              <button
                onClick={() => setShowAppMenu(true)}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 active:scale-90 ${
                  isLightMode ? "bg-zinc-100 border-zinc-250 hover:bg-zinc-200 text-zinc-700" : "bg-zinc-950/40 border-zinc-800 hover:bg-zinc-850 text-zinc-400"
                }`}
                title="Settings & Menu"
              >
                <FaBars className="text-sm" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 mt-8 animate-fade-in">
        
        {/* Hub Gateway Screen (Two big clean choices) */}
        {activeModule === "hub" && (
          <div className="space-y-12 py-4">
            
            {/* Standard greetings card */}
            <div className={`relative overflow-hidden border p-6 rounded-3xl backdrop-blur-xl shadow-xl transition-colors ${
              isLightMode ? "bg-white border-zinc-200 text-zinc-850" : "bg-gradient-to-br from-zinc-900/60 to-zinc-950 border-zinc-850 text-zinc-100"
            }`}>
              <div className="absolute top-0 right-0 w-48 h-48 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10">
                <h2 className="text-xl sm:text-2xl font-black">
                  {greeting}, {profile?.full_name || "User"}! 🌟
                </h2>
                <p className={`text-xs mt-1.5 leading-relaxed max-w-xl ${isLightMode ? "text-zinc-500" : "text-zinc-450"}`}>
                  Choose a module below to start tracking. Your fitness parameters and financial collaborative ledgers are kept fully isolated for high productivity.
                </p>
              </div>
            </div>

            {/* Hub Choice Grid */}
            <div className="grid md:grid-cols-2 gap-8">
              
              {/* Card 1: Calorie Tracker */}
              <div
                onClick={() => setActiveModule("calorie")}
                className={`group relative overflow-hidden border p-8 rounded-3xl backdrop-blur-md cursor-pointer transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl select-none ${
                  isLightMode
                    ? "bg-white border-zinc-200 hover:border-emerald-500/30 hover:shadow-emerald-500/5"
                    : "bg-gradient-to-b from-zinc-900/50 to-zinc-950 border-zinc-850 hover:border-emerald-500/30 hover:shadow-emerald-500/5"
                }`}
              >
                <div className="absolute -top-10 -right-10 w-36 h-36 bg-emerald-500/5 rounded-full blur-2xl group-hover:bg-emerald-500/10 transition-all duration-300" />
                <div className="flex flex-col h-full justify-between gap-8">
                  <div className="space-y-4">
                    <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center justify-center text-emerald-450 group-hover:scale-110 transition-transform duration-300 shadow-md">
                      <FaUtensils className="text-xl" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold group-hover:text-emerald-500 transition-colors duration-300">
                        Calorie & Macro Tracker
                      </h3>
                      <p className={`text-xs mt-2 leading-relaxed ${isLightMode ? "text-zinc-500" : "text-zinc-450"}`}>
                        Log food items, scan packaging barcodes, or use Qwen2.5-VL / Llama 3.3 models to automatically track macro metrics and caloric logs.
                      </p>
                    </div>
                  </div>

                  <div className={`border-t pt-6 flex items-center justify-between ${isLightMode ? "border-zinc-150" : "border-zinc-900"}`}>
                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                      Today: {calorieData.consumed_calories} / {calorieData.target_calories} kcal
                    </span>
                    <button className={`font-bold px-5 py-2 rounded-xl text-xs flex items-center gap-1 transition-all duration-300 ${
                      isLightMode
                        ? "border border-zinc-200 text-zinc-700 group-hover:bg-emerald-500 group-hover:text-zinc-950 group-hover:border-emerald-500"
                        : "border border-zinc-850 text-zinc-300 group-hover:bg-emerald-500 group-hover:text-zinc-950 group-hover:border-emerald-500"
                    }`}>
                      Open Tracker ➔
                    </button>
                  </div>
                </div>
              </div>

              {/* Card 2: Budget Planner */}
              <div
                onClick={() => setActiveModule("budget")}
                className={`group relative overflow-hidden border p-8 rounded-3xl backdrop-blur-md cursor-pointer transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl select-none ${
                  isLightMode
                    ? "bg-white border-zinc-200 hover:border-blue-500/30 hover:shadow-blue-500/5"
                    : "bg-gradient-to-b from-zinc-900/50 to-zinc-950 border-zinc-850 hover:border-blue-500/30 hover:shadow-blue-500/5"
                }`}
              >
                <div className="absolute -top-10 -right-10 w-36 h-36 bg-blue-500/5 rounded-full blur-2xl group-hover:bg-blue-500/10 transition-all duration-300" />
                <div className="flex flex-col h-full justify-between gap-8">
                  <div className="space-y-4">
                    <div className="w-14 h-14 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform duration-300 shadow-md">
                      <FaWallet className="text-xl" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold group-hover:text-blue-400 transition-colors duration-300">
                        Expense & Budget Planner
                      </h3>
                      <p className={`text-xs mt-2 leading-relaxed ${isLightMode ? "text-zinc-500" : "text-zinc-450"}`}>
                        Log personal expenses, coordinate collaborative spending accounts with partners, and review monthly breakdowns in INR/USD.
                      </p>
                    </div>
                  </div>

                  <div className={`border-t pt-6 flex items-center justify-between ${isLightMode ? "border-zinc-150" : "border-zinc-900"}`}>
                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                      Month Spent: {getCurrencySymbol()}{budgetData.monthly_total.toFixed(0)}
                    </span>
                    <button className={`font-bold px-5 py-2 rounded-xl text-xs flex items-center gap-1 transition-all duration-300 ${
                      isLightMode
                        ? "border border-zinc-200 text-zinc-700 group-hover:bg-blue-500 group-hover:text-zinc-950 group-hover:border-blue-500"
                        : "border border-zinc-850 text-zinc-300 group-hover:bg-blue-500 group-hover:text-zinc-950 group-hover:border-blue-500"
                    }`}>
                      Open Planner ➔
                    </button>
                  </div>
                </div>
              </div>

            </div>

          </div>
        )}

        {/* Tab 1: Calorie Tracker */}
        {activeModule === "calorie" && (
          <div className="space-y-8 animate-fade-in">
            
            {/* Header banner with Settings/Profile edit */}
            <div key={activeModule} className={`relative overflow-hidden border p-6 rounded-3xl backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center md:justify-between gap-4 animate-fade-in transition-colors ${
              isLightMode ? "bg-white border-zinc-200 text-zinc-850" : "bg-gradient-to-br from-zinc-900/60 to-zinc-950 border-zinc-850 text-zinc-100"
            }`}>
              <div>
                <h2 className="text-xl sm:text-2xl font-black text-zinc-150">
                  Calorie & Macro Tracker 🥗
                </h2>
                <p className={`text-xs mt-1.5 leading-relaxed max-w-xl ${isLightMode ? "text-zinc-500" : "text-zinc-400"}`}>
                  💡 **Calorie Progress**: You logged **{calorieData.consumed_calories} kcal** out of your daily target of {calorieData.target_calories} kcal. Click the settings gear to update your weight progress.
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => setShowProfileModal(true)}
                  className={`flex items-center gap-2 border px-4 py-2.5 rounded-2xl text-xs font-bold transition-all duration-300 hover:scale-105 active:scale-95 ${
                    isLightMode ? "bg-zinc-100 border-zinc-200 hover:border-emerald-500/20 text-zinc-700" : "bg-zinc-900 border-zinc-800 hover:border-emerald-500/30 text-zinc-200"
                  }`}
                >
                  <FaCog className="text-emerald-450" />
                  Update Goals / Weight
                </button>
                
                <div className="flex items-center gap-3 bg-emerald-500/5 border border-emerald-500/10 px-4 py-3 rounded-2xl select-none transition-all duration-300 hover:scale-105">
                  <FaFire className="text-emerald-455 text-sm animate-bounce" />
                  <div className="text-[10px]">
                    <span className="block text-zinc-500 font-bold uppercase">Remaining Calories</span>
                    <span className="text-emerald-400 font-bold mt-0.5 block text-xs">
                      {calorieData.remaining_calories} kcal left
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Core calorie logging forms & views */}
            <div className="grid lg:grid-cols-12 gap-8">
              
              {/* Left Column: Metrics & Charts */}
              <div className="lg:col-span-8 space-y-8">
                
                {/* Target summary rings */}
                <div className={`grid md:grid-cols-12 gap-6 border p-6 rounded-3xl backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  <div className="md:col-span-5 flex flex-col items-center justify-center border-r border-zinc-850/80 pr-2">
                    <span className="text-xs font-bold text-zinc-450 uppercase tracking-wider mb-4">Daily Calorie Balance</span>
                    <div className="relative w-36 h-36 flex items-center justify-center transition-all duration-500 hover:scale-105">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="transparent" stroke={isLightMode ? "#e4e4e7" : "#1c1c1e"} strokeWidth="7" />
                        <circle
                          cx="50"
                          cy="50"
                          r="40"
                          fill="transparent"
                          stroke="url(#calGrad)"
                          strokeWidth="7"
                          strokeDasharray={251.2}
                          strokeDashoffset={251.2 - (251.2 * calPct) / 100}
                          strokeLinecap="round"
                        />
                        <defs>
                          <linearGradient id="calGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#10b981" />
                            <stop offset="100%" stopColor="#14b8a6" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute flex flex-col items-center justify-center text-center">
                        <span className="text-2xl font-black">{calorieData.consumed_calories}</span>
                        <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mt-0.5">
                          of {calorieData.target_calories} kcal
                        </span>
                      </div>
                    </div>

                    <span className="text-xs mt-4">
                      {calorieData.remaining_calories > 0 ? (
                        <>You have <strong className="text-emerald-500">{calorieData.remaining_calories} kcal</strong> left</>
                      ) : (
                        <span className="text-red-500 font-bold flex items-center gap-1">
                          <FaExclamationTriangle className="text-[10px]" /> Target Limit Exceeded!
                        </span>
                      )}
                    </span>
                  </div>

                  <div className="md:col-span-7 flex flex-col justify-center gap-4 pl-2">
                    <span className="text-xs font-bold text-zinc-450 uppercase tracking-wider">Macronutrients Breakdown</span>
                    
                    {/* Protein */}
                    <div className="transition-all duration-300 hover:translate-x-1">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-semibold">Protein</span>
                        <span className="text-emerald-500 font-bold">
                          {calorieData.consumed_protein.toFixed(1)}g / {calorieData.target_protein}g
                        </span>
                      </div>
                      <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900">
                        <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${pPct}%` }} />
                      </div>
                    </div>

                    {/* Carbs */}
                    <div className="transition-all duration-300 hover:translate-x-1">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-semibold">Carbs</span>
                        <span className="text-yellow-500 font-bold">
                          {calorieData.consumed_carbs.toFixed(1)}g / {calorieData.target_carbs}g
                        </span>
                      </div>
                      <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900">
                        <div className="bg-yellow-500 h-full rounded-full transition-all duration-500" style={{ width: `${cPct}%` }} />
                      </div>
                    </div>

                    {/* Fat */}
                    <div className="transition-all duration-300 hover:translate-x-1">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-semibold">Fat</span>
                        <span className="text-pink-500 font-bold">
                          {calorieData.consumed_fat.toFixed(1)}g / {calorieData.target_fat}g
                        </span>
                      </div>
                      <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900">
                        <div className="bg-pink-500 h-full rounded-full transition-all duration-500" style={{ width: `${fPct}%` }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 7-Day Chart */}
                <div className={`border p-6 rounded-3xl backdrop-blur-md transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4 block">7-Day Caloric Intake diary</span>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={calorieData.history_7_days} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorCal" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis
                          dataKey="date"
                          stroke="#71717a"
                          fontSize={10}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(str) => {
                            const parts = str.split("-");
                            return parts[2] ? `${parts[1]}/${parts[2]}` : str;
                          }}
                        />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "12px", fontSize: "12px" }}
                          labelStyle={{ color: "#a1a1aa", fontWeight: "bold" }}
                        />
                        <Area type="monotone" dataKey="calories" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorCal)" name="Calories" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Scan Queue — one card per item, never overwritten */}
                {scanQueue.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <FaCheck className="text-emerald-500 text-xs" />
                      <span className={`text-xs font-bold uppercase tracking-wider ${isLightMode ? "text-zinc-500" : "text-zinc-400"}`}>
                        Scan Queue — {scanQueue.length} item{scanQueue.length > 1 ? "s" : ""} pending
                      </span>
                    </div>

                    {scanQueue.map((item) => {
                      const qty = scanQtys[item._id] ?? 1;
                      const sourceIcon = item._source === "image" ? "📷" : item._source === "barcode" ? "🔖" : "✍️";
                      return (
                        <div key={item._id} className={`border rounded-3xl relative overflow-hidden shadow-lg transition-all duration-300 ${isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/90 border-emerald-500/20"}`}>
                          <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 rounded-full blur-xl" />

                          {/* Card Header */}
                          <div className={`flex items-center justify-between px-5 py-3 border-b ${isLightMode ? "border-zinc-100 bg-zinc-50" : "border-zinc-800 bg-zinc-950/40"}`}>
                            <span className="text-xs font-bold text-emerald-500 flex items-center gap-1.5">
                              {sourceIcon} Scanned at {item._time}
                              {item._filename && <span className={`font-normal ml-1 ${isLightMode ? "text-zinc-400" : "text-zinc-500"}`}>· {item._filename}</span>}
                            </span>
                            <button
                              type="button"
                              onClick={() => dismissScanItem(item._id)}
                              className={`text-xs px-3 py-1 rounded-lg font-semibold transition-all active:scale-95 ${isLightMode ? "text-zinc-400 hover:text-red-500 hover:bg-red-50" : "text-zinc-500 hover:text-red-400 hover:bg-red-500/10"}`}
                            >
                              ✕ Dismiss
                            </button>
                          </div>

                          <div className="p-5 space-y-4">
                            <div>
                              <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Food Name</label>
                              <input
                                type="text"
                                value={item.food_name}
                                onChange={(e) => updateQueueItem(item._id, "food_name", e.target.value)}
                                className={`w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 transition-colors ${isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-900" : "bg-zinc-950/60 border-zinc-800 text-zinc-100"}`}
                              />
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                              <div>
                                <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Calories</label>
                                <input type="number" value={item.calories}
                                  onChange={(e) => updateQueueItem(item._id, "calories", parseInt(e.target.value) || 0)}
                                  className={`w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 text-center ${isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-900" : "bg-zinc-950/60 border-zinc-800 text-zinc-100"}`}
                                />
                              </div>
                              <div>
                                <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Protein (g)</label>
                                <input type="number" step="0.1" value={item.protein}
                                  onChange={(e) => updateQueueItem(item._id, "protein", parseFloat(e.target.value) || 0)}
                                  className={`w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 text-center ${isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-900" : "bg-zinc-950/60 border-zinc-800 text-zinc-100"}`}
                                />
                              </div>
                              <div>
                                <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Carbs (g)</label>
                                <input type="number" step="0.1" value={item.carbs}
                                  onChange={(e) => updateQueueItem(item._id, "carbs", parseFloat(e.target.value) || 0)}
                                  className={`w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 text-center ${isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-900" : "bg-zinc-950/60 border-zinc-800 text-zinc-100"}`}
                                />
                              </div>
                              <div>
                                <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Fat (g)</label>
                                <input type="number" step="0.1" value={item.fat}
                                  onChange={(e) => updateQueueItem(item._id, "fat", parseFloat(e.target.value) || 0)}
                                  className={`w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 text-center ${isLightMode ? "bg-zinc-100 border-zinc-200 text-zinc-900" : "bg-zinc-950/60 border-zinc-800 text-zinc-100"}`}
                                />
                              </div>
                            </div>

                            <div className={`flex items-center justify-between p-3 border rounded-2xl ${isLightMode ? "bg-zinc-50 border-zinc-200" : "bg-zinc-950/50 border-zinc-850"}`}>
                              <div className="text-xs">
                                <span className={`block font-semibold uppercase tracking-wider ${isLightMode ? "text-zinc-500" : "text-zinc-400"}`}>Servings</span>
                                <span className={`text-[10px] mt-0.5 block ${isLightMode ? "text-zinc-400" : "text-zinc-500"}`}>Scale portions (e.g. 2x)</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <button type="button"
                                  onClick={() => setScanQtys((prev) => ({ ...prev, [item._id]: Math.max(0.5, (prev[item._id] ?? 1) - 0.5) }))}
                                  className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-sm transition-all active:scale-75 ${isLightMode ? "bg-zinc-200 text-zinc-800" : "bg-zinc-800 text-zinc-200"}`}
                                >-</button>
                                <span className="font-bold w-12 text-center text-sm text-emerald-500">{qty}x</span>
                                <button type="button"
                                  onClick={() => setScanQtys((prev) => ({ ...prev, [item._id]: (prev[item._id] ?? 1) + 0.5 }))}
                                  className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-sm transition-all active:scale-75 ${isLightMode ? "bg-zinc-200 text-zinc-800" : "bg-zinc-800 text-zinc-200"}`}
                                >+</button>
                              </div>
                            </div>

                            <div className={`flex items-center justify-between border-t pt-4 ${isLightMode ? "border-zinc-100" : "border-zinc-850"}`}>
                              <span className={`text-xs ${isLightMode ? "text-zinc-400" : "text-zinc-500"}`}>
                                Total: <strong className="text-emerald-500">{Math.round(item.calories * qty)} kcal</strong>
                              </span>
                              <button
                                type="button"
                                onClick={() => submitScanItem(item)}
                                className="bg-gradient-to-r from-emerald-500 to-teal-500 text-zinc-950 font-bold px-6 py-2.5 rounded-xl text-sm shadow-md transition-all hover:brightness-110 active:scale-95"
                              >
                                Log Meal ✓
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Log List */}
                <div className={`border p-6 rounded-3xl backdrop-blur-md transition-all duration-300 hover:border-zinc-800 ${isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"}`}>
                  <span className="text-xs font-bold text-zinc-450 uppercase tracking-wider mb-4 block">Today's Meal Ledger</span>
                  {calorieData.logs.length === 0 ? (
                    <div className="text-center py-8 text-xs text-zinc-500 leading-relaxed">
                      No calorie records logged for today.<br />Use the calculator inputs on the right to scan meals!
                    </div>
                  ) : (
                    <div className="divide-y divide-zinc-900">
                      {calorieData.logs.map((l: any) => (
                        <div key={l.id} className="py-3.5 flex justify-between items-center first:pt-0 last:pb-0 transition-all duration-300 hover:bg-zinc-950/20 px-2 rounded-xl">
                          <div>
                            <span className="font-bold text-sm block">{l.food_name}</span>
                            <div className="flex gap-2 mt-1.5">
                              <span className="text-[9px] bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 px-2 py-0.5 rounded-md font-semibold">P: {l.protein}g</span>
                              <span className="text-[9px] bg-yellow-555/10 text-yellow-450 border border-yellow-555/20 px-2 py-0.5 rounded-md font-semibold">C: {l.carbs}g</span>
                              <span className="text-[9px] bg-pink-500/10 text-pink-400 border border-pink-500/20 px-2 py-0.5 rounded-md font-semibold">F: {l.fat}g</span>
                            </div>
                          </div>
                          <span className="text-sm font-bold text-emerald-555 bg-emerald-500/5 px-3.5 py-2 rounded-xl border border-emerald-500/10">
                            +{l.calories} kcal
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: Logging tools */}
              <div className="lg:col-span-4 space-y-6">
                
                {/* Option 1: Description Parser */}
                <div className={`border p-5 rounded-3xl backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:border-zinc-800 ${isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"}`}>
                  {scanPulse && (
                    <div className="absolute inset-0 bg-emerald-500/5 animate-pulse flex items-center justify-center z-10 backdrop-blur-[1px]">
                      <div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                  <h4 className="text-sm font-bold flex items-center gap-2 mb-3">
                    <FaSearch className="text-xs text-emerald-400" /> Food Description Parser
                  </h4>
                  <p className="text-[10px] text-zinc-500 mb-3 leading-relaxed">
                    Enter your meal description. Estimates are run via meta-llama/Llama-3.3-70B-Instruct to compile macros.
                  </p>
                  <form onSubmit={handleParseFood} className="space-y-3">
                    <input
                      type="text"
                      value={foodDesc}
                      onChange={(e) => setFoodDesc(e.target.value)}
                      placeholder="e.g. 2 slices of bread"
                      className="w-full bg-zinc-950/20 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs placeholder-zinc-700 focus:outline-none focus:border-emerald-500 transition-all duration-300"
                      required
                    />
                    <button
                      type="submit"
                      className="w-full bg-zinc-850 text-zinc-350 hover:bg-zinc-800 border border-zinc-750 font-semibold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center transition-all duration-300 active:scale-95"
                    >
                      Analyze Text Description
                    </button>
                  </form>
                </div>

                {/* Option 2: Image scanning */}
                <div className={`border p-5 rounded-3xl backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:border-zinc-800 ${isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"}`}>
                  {scanPulse && (
                    <div className="absolute inset-0 bg-emerald-500/5 animate-pulse flex items-center justify-center z-10 backdrop-blur-[1px]">
                      <div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                  <h4 className="text-sm font-bold flex items-center gap-2 mb-3">
                    <FaCamera className="text-xs text-emerald-400 animate-pulse" /> AI Food Picture Scan
                  </h4>
                  <p className="text-[10px] text-zinc-500 mb-3 leading-relaxed">
                    Upload an image of your meal to let Qwen2.5-VL identify food items and estimate portion targets.
                  </p>
                  <div className="flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-2xl p-4 bg-zinc-950/10 hover:border-emerald-500/40 transition-all duration-300 relative cursor-pointer group hover:scale-[1.02]">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                      className="absolute inset-0 opacity-0 cursor-pointer"
                    />
                    <FaCamera className="text-lg text-zinc-600 mb-2 group-hover:text-emerald-400 transition-colors duration-300" />
                    <span className="text-[10px] text-zinc-500 text-center group-hover:text-zinc-300 transition-colors duration-300">
                      {imageFile ? imageFile.name : "Click to select food picture"}
                    </span>
                  </div>
                </div>

                {/* Option 3: Barcode scanning simulator */}
                <div className={`border p-5 rounded-3xl backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:border-zinc-800 ${isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"}`}>
                  {scanPulse && (
                    <div className="absolute inset-0 bg-emerald-500/5 animate-pulse flex items-center justify-center z-10 backdrop-blur-[1px]">
                      <div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                  <h4 className="text-sm font-bold flex items-center gap-2 mb-3">
                    <FaBarcode className="text-xs text-emerald-400" /> Barcode Scan Simulator
                  </h4>
                  <p className="text-[10px] text-zinc-500 mb-3 leading-relaxed">
                    Lookup nutritional data. Select a preset barcode model below to simulate lookup:
                  </p>

                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => handleBarcodeLookup("737628064502")}
                      className="bg-zinc-950 border border-zinc-850 hover:border-emerald-500/20 hover:text-emerald-400 text-[10px] text-zinc-450 font-semibold py-2 rounded-xl transition-all duration-300 hover:scale-105 active:scale-95"
                    >
                      Rice Noodles
                    </button>
                    <button
                      type="button"
                      onClick={() => handleBarcodeLookup("5449000000996")}
                      className="bg-zinc-950 border border-zinc-850 hover:border-emerald-500/20 hover:text-emerald-400 text-[10px] text-zinc-455 font-semibold py-2 rounded-xl transition-all duration-300 hover:scale-105 active:scale-95"
                    >
                      Coca Cola Can
                    </button>
                  </div>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={barcodeInput}
                      onChange={(e) => setBarcodeInput(e.target.value)}
                      placeholder="Enter barcode number"
                      className="flex-1 bg-zinc-950/20 border border-zinc-800 rounded-xl px-3 py-2 text-[10px] placeholder-zinc-700 focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="button"
                      onClick={() => handleBarcodeLookup(barcodeInput)}
                      className="bg-zinc-850 border border-zinc-750 text-[10px] px-3 font-semibold rounded-xl text-zinc-350 hover:bg-zinc-800 transition-colors duration-305 active:scale-95"
                    >
                      Scan
                    </button>
                  </div>
                </div>

              </div>

            </div>
          </div>
        )}

        {/* Tab 2: Budget Calculator */}
        {activeModule === "budget" && (
          <div className="space-y-8 animate-fade-in">
            
            {/* Header banner with details */}
            <div key={activeModule} className={`relative overflow-hidden border p-6 rounded-3xl backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center md:justify-between gap-4 animate-fade-in transition-colors ${
              isLightMode ? "bg-white border-zinc-200 text-zinc-850" : "bg-gradient-to-br from-zinc-900/60 to-zinc-950 border-zinc-850 text-zinc-100"
            }`}>
              <div>
                <h2 className="text-xl sm:text-2xl font-black text-zinc-150">
                  Expense & Budget Planner 💳
                </h2>
                <p className={`text-xs mt-1.5 leading-relaxed max-w-xl ${isLightMode ? "text-zinc-500" : "text-zinc-400"}`}>
                  💡 **Budget Progress**: Your monthly total logged is **{getCurrencySymbol()}{budgetData.monthly_total.toFixed(2)}**. Share collaborations to coordinate ledger additions with partners.
                </p>
              </div>

              <div className="flex items-center gap-3 bg-blue-500/5 border border-blue-500/10 px-4 py-3 rounded-2xl shrink-0 select-none transition-all duration-300 hover:scale-105">
                <FaCoins className="text-blue-400 text-sm" />
                <div className="text-[10px]">
                  <span className="block text-zinc-550 font-bold uppercase">Collaborations Active</span>
                  <span className="text-blue-400 font-bold mt-0.5 block text-xs">
                    {budgetData.collaborations.filter((c: any) => c.status === "accepted").length} Ledger(s) Connected
                  </span>
                </div>
              </div>
            </div>

            {/* Core budget ledger forms & charts */}
            <div className="grid lg:grid-cols-12 gap-8">
              
              {/* Left Column: Totals & Lists */}
              <div className="lg:col-span-8 space-y-8">
                
                {/* Grand Total Spent Card */}
                <div className={`border p-6 rounded-3xl backdrop-blur-md relative overflow-hidden shadow-lg transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl" />
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">Monthly Expenditure Ledger</span>
                    <span className="text-[10px] font-semibold text-zinc-555 uppercase">Currency Context: {currency}</span>
                  </div>
                  
                  <div className="flex items-baseline gap-3">
                    <span className="text-5xl font-black text-blue-405 transition-all duration-500">
                      {getCurrencySymbol()}{(budgetData.expense_total ?? budgetData.personal_total + budgetData.collaborative_total).toFixed(2)}
                    </span>
                    <span className="text-xs text-zinc-400">summed total expenditure</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-zinc-850">
                    <div className="transition-all duration-300 hover:translate-x-1">
                      <span className="text-[10px] text-zinc-555 font-semibold block uppercase">Personal Spendings</span>
                      <span className="text-lg font-bold text-zinc-300 block mt-0.5">
                        {getCurrencySymbol()}{budgetData.personal_total.toFixed(2)}
                      </span>
                    </div>
                    <div className="transition-all duration-300 hover:translate-x-1">
                      <span className="text-[10px] text-zinc-555 font-semibold block uppercase">Shared Spendings</span>
                      <span className="text-lg font-bold text-blue-405 block mt-0.5">
                        {getCurrencySymbol()}{budgetData.collaborative_total.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Transactions Ledger */}
                <div className={`border p-6 rounded-3xl backdrop-blur-md transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4 block">Transactions Ledger</span>
                  {budgetData.transactions.length === 0 ? (
                    <div className="text-center py-10 text-xs text-zinc-555 leading-relaxed">
                      No expenditures logged for this month.<br />Add personal or collaborative transactions on the right to start!
                    </div>
                  ) : (
                    <div className="divide-y divide-zinc-900">
                      {budgetData.transactions.map((t: any) => (
                        <div key={t.id} className="py-3.5 flex justify-between items-center first:pt-0 last:pb-0 transition-all duration-300 hover:bg-zinc-950/20 px-2 rounded-xl">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm">{t.reason}</span>
                              <span className="text-[9px] bg-zinc-950 border border-zinc-850 text-zinc-555 px-2 py-0.5 rounded-full font-semibold">
                                {t.category}
                              </span>
                              {t.is_collaborative && (
                                <span className="text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full font-bold">
                                  Shared
                                </span>
                              )}
                            </div>
                            <span className="text-[9px] text-zinc-500 mt-1 block">
                              Logged date: {t.date}
                            </span>
                          </div>
                          <span className="text-sm font-bold text-blue-400 bg-blue-500/5 px-3 py-1.5 rounded-xl border border-blue-500/10">
                            {getCurrencySymbol()}{t.amount.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: Logging tools & Analytics */}
              <div className="lg:col-span-4 space-y-6">
                
                {/* Record expenditure form */}
                <div className={`border p-5 rounded-3xl backdrop-blur-md transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  
                  <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-850/60">
                    <h4 className="text-sm font-bold flex items-center gap-2">
                      <FaPlus className="text-xs text-blue-400" /> Log Expenditure
                    </h4>
                    
                    {/* Metric Switcher inside log card */}
                    <div className="flex items-center bg-zinc-950 border border-zinc-850 rounded-xl p-0.5 text-[9px] font-bold select-none">
                      <button
                        type="button"
                        onClick={() => setCurrency("INR")}
                        className={`px-2 py-1 rounded-lg transition-all duration-300 ${
                          currency === "INR"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                            : "text-zinc-500 hover:text-zinc-350"
                        }`}
                      >
                        ₹ INR
                      </button>
                      <button
                        type="button"
                        onClick={() => setCurrency("USD")}
                        className={`px-2 py-1 rounded-lg transition-all duration-300 ${
                          currency === "USD"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                            : "text-zinc-500 hover:text-zinc-350"
                        }`}
                      >
                        $ USD
                      </button>
                    </div>
                  </div>

                  <form onSubmit={handleAddTransaction} className="space-y-4">
                    <div>
                      <label className="block text-[10px] font-semibold text-zinc-555 uppercase tracking-wider mb-1.5">
                        Amount ({getCurrencySymbol()})
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-zinc-400 font-bold text-xs">
                          {getCurrencySymbol()}
                        </div>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="0.00"
                          value={bgAmount}
                          onChange={(e) => setBgAmount(e.target.value)}
                          className="w-full bg-zinc-950/20 border border-zinc-800 rounded-xl pl-8 pr-4 py-2 text-xs text-zinc-100 placeholder-zinc-750 focus:outline-none focus:border-blue-500 transition-all duration-350"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-zinc-555 uppercase tracking-wider mb-1.5">Reason (Why?)</label>
                      <input
                        type="text"
                        placeholder="e.g. Weekly Groceries"
                        value={bgReason}
                        onChange={(e) => setBgReason(e.target.value)}
                        className="w-full bg-zinc-950/20 border border-zinc-800 rounded-xl px-4 py-2 text-xs text-zinc-100 placeholder-zinc-750 focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] font-semibold text-zinc-555 uppercase tracking-wider mb-1.5">Category</label>
                        <select
                          value={bgCategory}
                          onChange={(e) => setBgCategory(e.target.value)}
                          className="w-full bg-zinc-950/20 border border-zinc-800 rounded-xl px-3 py-2 text-[11px] text-zinc-300 focus:outline-none focus:border-blue-500"
                        >
                          <option>Food</option>
                          <option>Travel</option>
                          <option>Rent</option>
                          <option>Entertainment</option>
                          <option>Health</option>
                          <option>Other</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] font-semibold text-zinc-555 uppercase tracking-wider mb-1.5">Date</label>
                        <input
                          type="date"
                          value={bgDate}
                          onChange={(e) => setBgDate(e.target.value)}
                          className="w-full bg-zinc-950/20 border border-zinc-800 rounded-xl px-3 py-2 text-[11px] text-zinc-300 focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>

                    {/* Collaboration toggle */}
                    {budgetData.collaborations.filter((c: any) => c.status === "accepted").length > 0 && (
                      <div className="bg-zinc-950/20 p-3 rounded-2xl border border-zinc-850/85 space-y-3 animate-slide-in">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-zinc-400 font-semibold uppercase">Shared/Collaborative expense</label>
                          <input
                            type="checkbox"
                            checked={bgCollaborative}
                            onChange={(e) => setBgCollaborative(e.target.checked)}
                            className="accent-blue-500 w-4 h-4 rounded transition-all duration-300"
                          />
                        </div>

                        {bgCollaborative && (
                          <div className="animate-fade-in">
                            <label className="block text-[9px] text-zinc-555 font-semibold uppercase mb-1">Select Shared Ledger</label>
                            <select
                              value={bgCollabId}
                              onChange={(e) => setBgCollabId(e.target.value)}
                              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-2 py-1.5 text-[10px] focus:outline-none"
                              required
                            >
                              <option value="">-- Select Collab partner --</option>
                              {budgetData.collaborations
                                .filter((c: any) => c.status === "accepted")
                                .map((c: any) => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                            </select>
                          </div>
                        )}
                      </div>
                    )}

                    <button
                      type="submit"
                      className="w-full bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-400 hover:to-indigo-400 text-zinc-950 font-black py-2.5 px-4 rounded-xl text-xs transition-all duration-300 shadow-md shadow-blue-500/5 active:scale-95 mt-2"
                    >
                      Log Expense
                    </button>
                  </form>
                </div>

                {/* Category Breakdown list */}
                {budgetData.transactions.length > 0 && (
                  <div className={`border p-5 rounded-3xl backdrop-blur-md space-y-4 transition-all duration-300 hover:border-zinc-800 ${
                    isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                  }`}>
                    <h4 className="text-sm font-bold flex items-center gap-2">
                      <FaCoins className="text-xs text-blue-400" /> Category Breakdown
                    </h4>
                    <div className="space-y-3.5 mt-2">
                      {["Food", "Travel", "Rent", "Entertainment", "Health", "Other"].map((cat) => {
                        const total = categoryTotals[cat] || 0;
                        const percentage = Math.round((total / maxCategoryTotal) * 100);
                        return (
                          <div key={cat} className="space-y-1 transition-all duration-300 hover:translate-x-1">
                            <div className="flex justify-between text-xs font-semibold">
                              <span className="text-zinc-405">{cat}</span>
                              <span className="text-zinc-205">
                                {getCurrencySymbol()}{total.toFixed(0)}
                              </span>
                            </div>
                            <div className="w-full bg-zinc-950 h-1.5 rounded-full overflow-hidden border border-zinc-900">
                              <div className="bg-blue-500 h-full rounded-full transition-all duration-500" style={{ width: `${percentage}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Collaboration invites */}
                <div className={`border p-5 rounded-3xl backdrop-blur-md space-y-4 transition-all duration-300 hover:border-zinc-800 ${
                  isLightMode ? "bg-white border-zinc-200" : "bg-zinc-900/30 border-zinc-850"
                }`}>
                  <h4 className="text-sm font-bold flex items-center gap-2">
                    <FaUserFriends className="text-xs text-blue-400" /> Collaboration Ledger
                  </h4>
                  <p className="text-[10px] text-zinc-555 leading-relaxed">
                    Invite another user to share accounts and co-author budgets in real-time.
                  </p>

                  <form onSubmit={handleSendInvite} className="space-y-3">
                    <input
                      type="text"
                      value={partnerInput}
                      onChange={(e) => setPartnerInput(e.target.value)}
                      placeholder="Partner email or phone"
                      className="w-full bg-zinc-955/20 border border-zinc-800 rounded-xl px-3 py-2 text-[10px] placeholder-zinc-700 focus:outline-none focus:border-blue-500"
                      required
                    />
                    <input
                      type="text"
                      value={collabNameInput}
                      onChange={(e) => setCollabNameInput(e.target.value)}
                      placeholder="Shared Ledger Name"
                      className="w-full bg-zinc-955/20 border border-zinc-800 rounded-xl px-3 py-2 text-[10px] placeholder-zinc-705 focus:outline-none focus:border-blue-500"
                      required
                    />
                    <button
                      type="submit"
                      className="w-full bg-zinc-850 hover:bg-zinc-800 border border-zinc-750 text-zinc-200 font-semibold py-2 px-3 rounded-xl text-xs flex items-center justify-center transition-all duration-300 active:scale-95"
                    >
                      Send Invite
                    </button>
                  </form>

                  {budgetData.collaborations.length > 0 && (
                    <div className="space-y-2 border-t border-zinc-900 pt-4">
                      <span className="block text-[10px] font-bold text-zinc-450 uppercase mb-2">Connected Partners</span>
                      {budgetData.collaborations.map((c: any) => (
                        <div
                          key={c.id}
                          className="flex items-center justify-between p-2 rounded-xl bg-zinc-955/20 border border-zinc-850 text-xs transition-all duration-300 hover:scale-[1.02]"
                        >
                          <div>
                            <span className="font-semibold block">{c.name}</span>
                            <span className="text-[9px] text-zinc-555 block uppercase">Status: {c.status}</span>
                          </div>
                          {c.status === "pending" && c.partner_id === profile.id && (
                            <div className="flex gap-1.5">
                              <button
                                onClick={() => handleInviteResponse(c.id, "accepted")}
                                className="w-6 h-6 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 flex items-center justify-center transition-all duration-300 border border-emerald-500/20 active:scale-75"
                                title="Accept Invite"
                              >
                                <FaCheck className="text-[9px]" />
                              </button>
                              <button
                                onClick={() => handleInviteResponse(c.id, "rejected")}
                                className="w-6 h-6 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 flex items-center justify-center transition-all duration-300 border border-red-500/20 active:scale-75"
                                title="Reject Invite"
                              >
                                <FaTimes className="text-[9px]" />
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

            </div>
          </div>
        )}

      </main>

      {/* Slide-In Hamburger Menu Drawer overlay */}
      {showAppMenu && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop overlay */}
          <div
            onClick={() => setShowAppMenu(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
          />

          {/* Drawer Panel */}
          <div className="relative w-80 bg-zinc-900 border-l border-zinc-800 p-6 flex flex-col justify-between shadow-2xl z-10 animate-slide-in h-full text-zinc-200">
            <div>
              <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
                <span className="font-black text-emerald-450 text-sm tracking-wider uppercase">Menu Navigation</span>
                <button
                  onClick={() => setShowAppMenu(false)}
                  className="w-8 h-8 rounded-full bg-zinc-950 flex items-center justify-center hover:bg-zinc-850 transition-colors border border-zinc-800"
                >
                  <FaTimes className="text-zinc-400 text-xs" />
                </button>
              </div>

              {/* User Bio Card */}
              <div className="bg-zinc-950 p-4 rounded-2xl border border-zinc-850 mb-6 flex items-center gap-3 select-none">
                <div className="w-10 h-10 bg-emerald-500/10 border border-emerald-500/25 rounded-full flex items-center justify-center text-emerald-400">
                  <FaUser className="text-sm" />
                </div>
                <div>
                  <span className="block font-bold text-xs text-zinc-200">{profile?.full_name || "Account Profile"}</span>
                  <span className="block text-[9px] text-zinc-500 mt-0.5">NutriBudget Member</span>
                </div>
              </div>

              {/* Actions List */}
              <div className="space-y-3">
                <button
                  onClick={() => {
                    setShowAppMenu(false);
                    setShowProfileModal(true);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-950/40 hover:bg-zinc-800 border border-zinc-850 text-xs font-semibold transition-all hover:translate-x-1"
                >
                  <FaCog className="text-emerald-400" />
                  Fitness Settings & Goals
                </button>

                <button
                  onClick={() => {
                    setShowAppMenu(false);
                    setShowPasswordModal(true);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-950/40 hover:bg-zinc-800 border border-zinc-850 text-xs font-semibold transition-all hover:translate-x-1"
                >
                  <FaLock className="text-yellow-450" />
                  Change Password
                </button>

                {/* Theme Selector Toggle */}
                <button
                  onClick={() => setIsLightMode(!isLightMode)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-zinc-950/40 hover:bg-zinc-800 border border-zinc-850 text-xs font-semibold transition-all hover:translate-x-1"
                >
                  <span className="flex items-center gap-3">
                    {isLightMode ? <FaSun className="text-amber-400" /> : <FaMoon className="text-blue-400" />}
                    <span>Theme: {isLightMode ? "Light Mode" : "Dark Mode"}</span>
                  </span>
                  <span className="text-[9px] bg-zinc-950 border border-zinc-800 px-2 py-0.5 rounded-md text-zinc-400">Toggle</span>
                </button>

                {/* Return to hub */}
                {activeModule !== "hub" && (
                  <button
                    onClick={() => {
                      setShowAppMenu(false);
                      setActiveModule("hub");
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-950/40 hover:bg-zinc-800 border border-zinc-850 text-xs font-semibold transition-all hover:translate-x-1"
                  >
                    <FaChevronLeft className="text-zinc-400 text-[10px]" />
                    Back to Dashboard Hub
                  </button>
                )}
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="space-y-3 pt-6 border-t border-zinc-800">
              <button
                onClick={() => {
                  setShowAppMenu(false);
                  setShowDeleteModal(true);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-xs font-bold text-red-400 transition-all active:scale-95"
              >
                <FaTrash className="text-xs" />
                Delete Account Permanently
              </button>

              <button
                onClick={() => {
                  setShowAppMenu(false);
                  handleLogout();
                }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-950/80 hover:bg-zinc-850 border border-zinc-800 text-xs font-bold text-zinc-350 transition-all active:scale-95"
              >
                <FaSignOutAlt className="text-xs text-zinc-450" />
                Sign Out / Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Profile settings metrics editor modal */}
      {showProfileModal && profile && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center px-4 animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl w-full max-w-lg p-6 relative shadow-2xl animate-slide-in max-h-[90vh] overflow-y-auto text-zinc-200">
            <button
              onClick={() => setShowProfileModal(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-250 w-8 h-8 rounded-full bg-zinc-950 flex items-center justify-center border border-zinc-850"
            >
              <FaTimes className="text-xs" />
            </button>

            <h3 className="text-md font-bold text-emerald-400 flex items-center gap-2 mb-4">
              <FaUser className="text-xs text-emerald-450 animate-pulse" /> Personal Metrics & Targets
            </h3>

            {/* Current Metrics Stats Badge */}
            <div className="bg-zinc-950/60 p-4 border border-zinc-850 rounded-2xl grid grid-cols-2 gap-y-3 gap-x-4 text-xs leading-relaxed">
              <div>
                <span className="text-zinc-555 block uppercase font-semibold text-[9px]">Full Name</span>
                <span className="text-zinc-350 font-bold block mt-0.5">{profile.full_name}</span>
              </div>
              <div>
                <span className="text-zinc-555 block uppercase font-semibold text-[9px]">Age / Sex</span>
                <span className="text-zinc-350 font-bold block mt-0.5">
                  {calculateAge(profile.date_of_birth)} years / {profile.sex}
                </span>
              </div>
              <div>
                <span className="text-zinc-555 block uppercase font-semibold text-[9px]">Height / Weight</span>
                <span className="text-zinc-350 font-bold block mt-0.5">
                  {profile.height_cm} cm / {profile.current_weight_kg} kg
                </span>
              </div>
              <div>
                <span className="text-zinc-555 block uppercase font-semibold text-[9px]">Goal Weight Target</span>
                <span className="text-zinc-350 font-bold block mt-0.5">
                  {profile.goal_weight_kg} kg ({profile.goal})
                </span>
              </div>
              <div className="border-t border-zinc-900 pt-3 col-span-2 grid grid-cols-3 gap-2">
                <div>
                  <span className="text-zinc-555 block uppercase font-bold text-[8px]">BMI Metric</span>
                  <span className="text-teal-400 font-extrabold text-sm">{profile.bmi.toFixed(1)}</span>
                </div>
                <div>
                  <span className="text-zinc-555 block uppercase font-bold text-[8px]">Maintenance (TDEE)</span>
                  <span className="text-emerald-400 font-extrabold text-sm">{profile.tdee.toFixed(0)} kcal</span>
                </div>
                <div>
                  <span className="text-zinc-555 block uppercase font-bold text-[8px]">Recommended Target</span>
                  <span className="text-emerald-450 font-extrabold text-sm">{profile.daily_calorie_target} kcal</span>
                </div>
              </div>
            </div>

            {/* Caloric Progression Info Card */}
            <div className="bg-emerald-500/5 border border-emerald-500/10 p-3 rounded-2xl text-xs space-y-1 mt-4">
              <span className="block font-bold text-emerald-455 uppercase text-[9px]">Caloric Progression Analysis</span>
              <span className="block text-zinc-300 leading-relaxed">
                Your maintenance calories (TDEE) based on current weight is <strong>{profile.tdee} kcal</strong>.
                {profile.goal === "lose" && ` To reduce weight from ${profile.current_weight_kg} kg to ${profile.goal_weight_kg} kg, a deficit of 500 kcal is applied. Recommended target: ${profile.daily_calorie_target} kcal/day.`}
                {profile.goal === "gain" && ` To gain muscle/weight from ${profile.current_weight_kg} kg to ${profile.goal_weight_kg} kg, a surplus of 300 kcal is applied. Recommended target: ${profile.daily_calorie_target} kcal/day.`}
                {profile.goal === "maintain" && ` To maintain weight at ${profile.current_weight_kg} kg, target is equal to your maintenance calories: ${profile.daily_calorie_target} kcal/day.`}
              </span>
            </div>

            {/* Editing Form */}
            <form onSubmit={handleUpdateProfile} className="space-y-4 mt-6">
              
              {/* Static display for Name, Sex, DOB to prevent edit */}
              <div className="p-3 bg-zinc-950/20 border border-zinc-900 rounded-2xl flex items-center justify-between text-[10px] text-zinc-500 select-none">
                <span>Account Parameters (Locked):</span>
                <span className="font-bold text-zinc-400">
                  {profile.full_name} | {profile.sex} | {profile.date_of_birth}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Current Weight (kg)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editWeight}
                    onChange={(e) => setEditWeight(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500 text-center text-zinc-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Target Goal Weight (kg)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editGoalWeight}
                    onChange={(e) => setEditGoalWeight(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500 text-center text-zinc-200"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Height (cm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editHeight}
                    onChange={(e) => setEditHeight(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500 text-center text-zinc-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Exercise Days / Week</label>
                  <input
                    type="number"
                    min="0"
                    max="7"
                    value={editExerciseDays}
                    onChange={(e) => setEditExerciseDays(parseInt(e.target.value) || 0)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-emerald-500 text-center text-zinc-200"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Weight Goal Target</label>
                  <select
                    value={editGoal}
                    onChange={(e) => setEditGoal(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-2 py-2 text-xs focus:outline-none focus:border-emerald-500 text-zinc-200"
                  >
                    <option value="lose">Weight Loss (Lose)</option>
                    <option value="maintain">Maintain Weight</option>
                    <option value="gain">Muscle Gain (Gain)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Activity Level</label>
                  <select
                    value={editActivity}
                    onChange={(e) => setEditActivity(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-2 py-2 text-xs focus:outline-none focus:border-emerald-500 text-zinc-200"
                  >
                    <option value="sedentary">Sedentary (desk job)</option>
                    <option value="light">Lightly Active</option>
                    <option value="moderate">Moderately Active</option>
                    <option value="very_active">Very Active</option>
                    <option value="athlete">Athlete / Heavy Training</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6 border-t border-zinc-850 pt-4">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="bg-zinc-950 border border-zinc-800 hover:bg-zinc-900 text-zinc-400 px-4 py-2 rounded-xl text-xs transition-all active:scale-95"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="bg-gradient-to-r from-emerald-500 to-teal-500 text-zinc-950 font-bold px-5 py-2 rounded-xl text-xs transition-all hover:brightness-110 active:scale-95 shadow-md shadow-emerald-500/10"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center px-4 animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl w-full max-w-sm p-6 relative shadow-2xl animate-slide-in text-zinc-200">
            <button
              onClick={() => setShowPasswordModal(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-250 w-8 h-8 rounded-full bg-zinc-950 flex items-center justify-center border border-zinc-850"
            >
              <FaTimes className="text-xs" />
            </button>

            <h3 className="text-md font-bold text-yellow-450 flex items-center gap-2 mb-4">
              <FaLock className="text-xs animate-pulse" /> Change Password
            </h3>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">Current Password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  className="w-full bg-zinc-955/20 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-yellow-500"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className="w-full bg-zinc-955/20 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-yellow-500"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 mt-6 border-t border-zinc-850 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="bg-zinc-955 border border-zinc-800 hover:bg-zinc-900 text-zinc-400 px-4 py-2 rounded-xl text-xs transition-all active:scale-95"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-gradient-to-r from-yellow-555 to-amber-500 text-zinc-950 font-bold px-5 py-2 rounded-xl text-xs transition-all hover:brightness-110 active:scale-95 shadow-md shadow-yellow-500/10"
                >
                  Change Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Account Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center px-4 animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl w-full max-w-sm p-6 relative shadow-2xl animate-slide-in text-zinc-200">
            <button
              onClick={() => setShowDeleteModal(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-250 w-8 h-8 rounded-full bg-zinc-950 flex items-center justify-center border border-zinc-850"
            >
              <FaTimes className="text-xs" />
            </button>

            <h3 className="text-md font-bold text-red-500 flex items-center gap-2 mb-2">
              <FaExclamationTriangle className="text-xs animate-bounce" /> Delete Account Permanently
            </h3>
            <p className="text-[10px] text-zinc-400 leading-relaxed mb-4">
              Warning: This will permanently wipe your physical metrics history, calorie logs, collaborations, and transactions. This cannot be undone.
            </p>

            <form onSubmit={handleDeleteAccount} className="space-y-4">
              <div>
                <label className="block text-[10px] text-zinc-500 font-semibold uppercase mb-1">
                  Type <strong className="text-zinc-200">"delete my account"</strong> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteConfirmationText}
                  onChange={(e) => setDeleteConfirmationText(e.target.value)}
                  placeholder="Type validation string"
                  className="w-full bg-zinc-955/20 border border-zinc-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-red-500 text-center"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 mt-6 border-t border-zinc-850 pt-4">
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(false)}
                  className="bg-zinc-955 border border-zinc-800 hover:bg-zinc-900 text-zinc-400 px-4 py-2 rounded-xl text-xs transition-all active:scale-95"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-red-500 hover:bg-red-400 text-zinc-950 font-bold px-5 py-2 rounded-xl text-xs transition-all active:scale-95 shadow-md shadow-red-500/10"
                >
                  Delete Permanently
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
