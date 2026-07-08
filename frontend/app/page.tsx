"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast, Toaster } from "sonner";
import { apiClient, getApiError } from "./api-client";

type AuthMode = "login" | "register" | "forgot";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [useEmail, setUseEmail] = useState(true);
  const [loading, setLoading] = useState(false);

  // Form states
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [otpSent, setOtpSent] = useState(false);

  const getIdentifier = () => {
    return useEmail ? email : phone;
  };

  const handleSendOtp = async () => {
    const id = getIdentifier();
    if (!id) {
      toast.error(useEmail ? "Please enter your email." : "Please enter your phone number.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.post("/auth/send-otp", {
        email_or_phone: id,
        purpose: mode === "register" ? "register" : "reset_password",
      });
      setOtpSent(true);
      toast.success(res.data.message || "OTP sent successfully!");
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = getIdentifier();
    if (!id || !password) {
      toast.error("Please fill in all fields.");
      return;
    }
    setLoading(true);
    try {
      const payload: any = { password };
      if (useEmail) payload.email = id;
      else payload.phone = id;

      const res = await apiClient.post("/auth/login", payload);
      localStorage.setItem("access_token", res.data.tokens.access_token);
      localStorage.setItem("refresh_token", res.data.tokens.refresh_token);
      
      toast.success("Welcome back! Logging in...");
      
      // Check if user has a profile
      try {
        await apiClient.get("/profile/me");
        router.push("/dashboard");
      } catch (profileErr) {
        // Redirect to onboarding if profile doesn't exist
        router.push("/profile-setup");
      }
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = getIdentifier();
    if (!id || !password || !otpCode) {
      toast.error("Please fill in all fields including the OTP.");
      return;
    }
    setLoading(true);
    try {
      const payload: any = { password, otp_code: otpCode };
      if (useEmail) payload.email = id;
      else payload.phone = id;

      const res = await apiClient.post("/auth/register", payload);
      localStorage.setItem("access_token", res.data.tokens.access_token);
      localStorage.setItem("refresh_token", res.data.tokens.refresh_token);
      
      toast.success("Account created successfully! Let's setup your profile.");
      router.push("/profile-setup");
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = getIdentifier();
    if (!id || !otpCode || !newPassword) {
      toast.error("Please fill in all fields.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.post("/auth/reset-password", {
        email_or_phone: id,
        otp_code: otpCode,
        new_password: newPassword,
      });
      toast.success(res.data.message || "Password reset successful! Sign in now.");
      setMode("login");
      setOtpSent(false);
      setOtpCode("");
      setNewPassword("");
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-zinc-950 font-sans text-zinc-200 overflow-hidden">
      <Toaster position="top-right" theme="dark" closeButton />

      {/* Decorative gradients */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/20 rounded-full blur-[128px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[450px] h-[450px] bg-teal-500/10 rounded-full blur-[160px] pointer-events-none" />

      {/* Glassmorphic Auth Card */}
      <div className="w-full max-w-md mx-4 bg-zinc-900/50 backdrop-blur-xl border border-zinc-800/80 rounded-3xl shadow-2xl p-8 relative z-10">
        
        {/* Brand header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            NutriBudget AI
          </h1>
          <p className="text-zinc-400 text-sm mt-2">
            AI Nutrition Scanner & Shared Budget Planner
          </p>
        </div>

        {/* Tab selector */}
        {mode !== "forgot" && (
          <div className="flex border border-zinc-800 rounded-xl p-1 bg-zinc-950/40 mb-6">
            <button
              onClick={() => {
                setMode("login");
                setOtpSent(false);
              }}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                mode === "login"
                  ? "bg-zinc-800 text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setMode("register");
                setOtpSent(false);
              }}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                mode === "register"
                  ? "bg-zinc-800 text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign Up
            </button>
          </div>
        )}

        {/* Email/Phone selector */}
        <div className="flex items-center justify-between text-xs text-zinc-400 mb-4 px-1">
          <span>Authentication Method:</span>
          <button
            onClick={() => setUseEmail(!useEmail)}
            className="text-emerald-400 hover:underline font-medium"
          >
            Switch to {useEmail ? "Phone" : "Email"}
          </button>
        </div>

        {/* Auth form */}
        {mode === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                {useEmail ? "Email Address" : "Phone Number"}
              </label>
              <input
                type={useEmail ? "email" : "tel"}
                placeholder={useEmail ? "you@example.com" : "+1234567890"}
                value={useEmail ? email : phone}
                onChange={(e) => (useEmail ? setEmail(e.target.value) : setPhone(e.target.value))}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                required
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setMode("forgot");
                    setOtpSent(false);
                  }}
                  className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors"
                >
                  Forgot Password?
                </button>
              </div>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-zinc-950 font-bold py-3 px-4 rounded-xl shadow-lg hover:shadow-emerald-500/10 transition-all duration-300 disabled:opacity-50 mt-6"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        )}

        {mode === "register" && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                {useEmail ? "Email Address" : "Phone Number"}
              </label>
              <div className="flex gap-2">
                <input
                  type={useEmail ? "email" : "tel"}
                  placeholder={useEmail ? "you@example.com" : "+1234567890"}
                  value={useEmail ? email : phone}
                  onChange={(e) => (useEmail ? setEmail(e.target.value) : setPhone(e.target.value))}
                  className="flex-1 bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={loading}
                  className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold px-4 rounded-xl text-xs transition-colors border border-zinc-750 disabled:opacity-50 whitespace-nowrap"
                >
                  {otpSent ? "Resend" : "Send OTP"}
                </button>
              </div>
            </div>

            {otpSent && (
              <div className="animate-fade-in">
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  Verification Code (OTP)
                </label>
                <input
                  type="text"
                  placeholder="123456"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 tracking-[0.25em] text-center font-mono text-lg focus:outline-none focus:border-emerald-500 transition-colors"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                type="password"
                placeholder="Min 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading || !otpSent}
              className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-zinc-950 font-bold py-3 px-4 rounded-xl shadow-lg hover:shadow-emerald-500/10 transition-all duration-300 disabled:opacity-50 mt-6"
            >
              {loading ? "Registering..." : "Register"}
            </button>
          </form>
        )}

        {mode === "forgot" && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <h3 className="text-zinc-300 text-sm font-bold mb-4 text-center">Reset Password</h3>
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                {useEmail ? "Email Address" : "Phone Number"}
              </label>
              <div className="flex gap-2">
                <input
                  type={useEmail ? "email" : "tel"}
                  placeholder={useEmail ? "you@example.com" : "+1234567890"}
                  value={useEmail ? email : phone}
                  onChange={(e) => (useEmail ? setEmail(e.target.value) : setPhone(e.target.value))}
                  className="flex-1 bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={loading}
                  className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold px-4 rounded-xl text-xs transition-colors border border-zinc-750 disabled:opacity-50 whitespace-nowrap"
                >
                  {otpSent ? "Resend" : "Send OTP"}
                </button>
              </div>
            </div>

            {otpSent && (
              <>
                <div className="animate-fade-in">
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Verification Code (OTP)
                  </label>
                  <input
                    type="text"
                    placeholder="123456"
                    maxLength={6}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 tracking-[0.25em] text-center font-mono text-lg focus:outline-none focus:border-emerald-500 transition-colors"
                    required
                  />
                </div>

                <div className="animate-fade-in">
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    placeholder="Min 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                    required
                  />
                </div>
              </>
            )}

            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setOtpSent(false);
                }}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold py-3 px-4 rounded-xl transition-colors border border-zinc-750"
              >
                Back to Login
              </button>
              <button
                type="submit"
                disabled={loading || !otpSent}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-zinc-950 font-bold py-3 px-4 rounded-xl shadow-lg transition-all duration-300 disabled:opacity-50"
              >
                {loading ? "Resetting..." : "Reset"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
