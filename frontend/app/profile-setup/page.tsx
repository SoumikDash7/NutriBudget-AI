"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast, Toaster } from "sonner";
import { apiClient, getApiError } from "../api-client";

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  // Form states
  const [fullName, setFullName] = useState("");
  const [sex, setSex] = useState("male");
  const [dob, setDob] = useState("1998-01-01");
  const [height, setHeight] = useState(175);
  const [weight, setWeight] = useState(70);
  const [goalWeight, setGoalWeight] = useState(70);
  const [goal, setGoal] = useState("maintain");
  const [activity, setActivity] = useState("moderate");
  const [exerciseDays, setExerciseDays] = useState(3);

  // Client-side previews
  const [bmi, setBmi] = useState(0);
  const [bmr, setBmr] = useState(0);
  const [tdee, setTdee] = useState(0);
  const [calories, setCalories] = useState(0);

  // Recalculate metrics whenever height, weight, sex, dob, goal, or activity changes
  useEffect(() => {
    // 1. BMI
    const hM = height / 100;
    const computedBmi = weight / (hM * hM);
    setBmi(parseFloat(computedBmi.toFixed(1)));

    // 2. Age from DOB
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    if (isNaN(age) || age < 0) age = 25; // fallback

    // 3. BMR (Mifflin-St Jeor)
    let computedBmr = 10 * weight + 6.25 * height - 5 * age;
    if (sex === "male") {
      computedBmr += 5;
    } else {
      computedBmr -= 161;
    }
    setBmr(Math.round(computedBmr));

    // 4. TDEE
    const multipliers: Record<string, number> = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      very_active: 1.725,
      athlete: 1.9,
    };
    const factor = multipliers[activity] || 1.2;
    const computedTdee = computedBmr * factor;
    setTdee(Math.round(computedTdee));

    // 5. Target Calories
    let computedCal = computedTdee;
    if (goal === "lose") {
      computedCal -= 500;
    } else if (goal === "gain") {
      computedCal += 300;
    }
    setCalories(Math.round(computedCal));
  }, [height, weight, sex, dob, goal, activity]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName) {
      toast.error("Please enter your name.");
      return;
    }

    setLoading(true);
    try {
      await apiClient.post("/profile", {
        full_name: fullName,
        sex: sex,
        date_of_birth: dob,
        height_cm: height,
        current_weight_kg: weight,
        goal_weight_kg: goalWeight,
        goal: goal,
        activity_level: activity,
        exercise_days_per_week: exerciseDays,
        preferred_unit: "metric",
      });
      toast.success("Profile saved successfully!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-zinc-950 font-sans text-zinc-200 overflow-hidden py-12">
      <Toaster position="top-right" theme="dark" />

      {/* Decorative gradients */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-teal-500/10 rounded-full blur-[150px] pointer-events-none" />

      <div className="w-full max-w-4xl mx-4 bg-zinc-900/50 backdrop-blur-xl border border-zinc-800/80 rounded-3xl shadow-2xl overflow-hidden grid md:grid-cols-12 relative z-10">
        
        {/* Onboarding Input Column */}
        <form onSubmit={handleSubmit} className="p-8 md:col-span-7 space-y-6">
          <div>
            <h2 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              Create Your Profile
            </h2>
            <p className="text-zinc-400 text-xs mt-1">
              Help us calibrate your personalized calorie and fitness targets.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Date of Birth
              </label>
              <input
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                required
              />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Gender
              </label>
              <select
                value={sex}
                onChange={(e) => setSex(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Target Weight (kg)
              </label>
              <input
                type="number"
                value={goalWeight}
                onChange={(e) => setGoalWeight(parseFloat(e.target.value) || 0)}
                placeholder="70"
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                required
              />
            </div>
          </div>

          {/* Sliders for weight/height */}
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1 text-sm">
                <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Height (cm)</label>
                <span className="font-bold text-emerald-400">{height} cm</span>
              </div>
              <input
                type="range"
                min={100}
                max={250}
                value={height}
                onChange={(e) => setHeight(parseInt(e.target.value))}
                className="w-full accent-emerald-500 bg-zinc-950 rounded-lg h-2"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-sm">
                <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Current Weight (kg)</label>
                <span className="font-bold text-emerald-400">{weight} kg</span>
              </div>
              <input
                type="range"
                min={30}
                max={200}
                value={weight}
                onChange={(e) => setWeight(parseInt(e.target.value))}
                className="w-full accent-emerald-500 bg-zinc-950 rounded-lg h-2"
              />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Caloric Goal
              </label>
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
              >
                <option value="lose">Lose Weight (-500 kcal)</option>
                <option value="maintain">Maintain Weight</option>
                <option value="gain">Gain Weight (+300 kcal)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                Activity Level
              </label>
              <select
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl px-4 py-2.5 text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
              >
                <option value="sedentary">Sedentary (Little to no exercise)</option>
                <option value="light">Lightly Active (1-3 days/wk)</option>
                <option value="moderate">Moderately Active (3-5 days/wk)</option>
                <option value="very_active">Very Active (6-7 days/wk)</option>
                <option value="athlete">Athlete (Twice daily training)</option>
              </select>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1 text-sm">
              <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Exercise Days per Week</label>
              <span className="font-bold text-emerald-400">{exerciseDays} Days</span>
            </div>
            <input
              type="range"
              min={0}
              max={7}
              value={exerciseDays}
              onChange={(e) => setExerciseDays(parseInt(e.target.value))}
              className="w-full accent-emerald-500 bg-zinc-950 rounded-lg h-2"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-zinc-950 font-bold py-3 px-4 rounded-xl shadow-lg transition-all duration-300 disabled:opacity-50 mt-4"
          >
            {loading ? "Saving Profile..." : "Complete Profile Setup"}
          </button>
        </form>

        {/* Live preview section */}
        <div className="bg-zinc-950/60 border-l border-zinc-800/80 p-8 md:col-span-5 flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-zinc-200">Personalized Insights</h3>
            <p className="text-zinc-500 text-xs mt-1">Calculated in real-time based on your measurements.</p>
          </div>

          {/* Metric cards */}
          <div className="space-y-6 my-8">
            <div className="bg-zinc-900/40 border border-zinc-850 p-4 rounded-2xl flex items-center justify-between">
              <div>
                <span className="text-xs text-zinc-500 font-medium block">Body Mass Index (BMI)</span>
                <span className="text-xl font-extrabold text-zinc-200 mt-1 block">{bmi}</span>
              </div>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                bmi < 18.5
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  : bmi < 25
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-red-500/10 text-red-400 border border-red-500/20"
              }`}>
                {bmi < 18.5 ? "Underweight" : bmi < 25 ? "Normal" : "Overweight"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-zinc-900/40 border border-zinc-850 p-4 rounded-2xl">
                <span className="text-xs text-zinc-500 font-medium block">BMR</span>
                <span className="text-lg font-bold text-zinc-300 mt-0.5 block">{bmr} kcal</span>
                <span className="text-[10px] text-zinc-500 mt-1 block">Baseline calories</span>
              </div>
              <div className="bg-zinc-900/40 border border-zinc-850 p-4 rounded-2xl">
                <span className="text-xs text-zinc-500 font-medium block">TDEE</span>
                <span className="text-lg font-bold text-zinc-300 mt-0.5 block">{tdee} kcal</span>
                <span className="text-[10px] text-zinc-500 mt-1 block">Activity factored</span>
              </div>
            </div>

            <div className="bg-zinc-900/60 border border-zinc-800 p-5 rounded-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl" />
              <span className="text-xs text-zinc-500 font-medium block">Recommended Daily Budget</span>
              <span className="text-3xl font-black text-emerald-400 mt-1.5 block">{calories} kcal</span>
              <span className="text-[10px] text-zinc-400 mt-2 block">
                Fulfilling this allows you to <strong className="text-zinc-200 font-bold">{goal === "lose" ? "lose weight" : goal === "gain" ? "gain weight" : "maintain weight"}</strong>.
              </span>
            </div>
          </div>

          <div className="text-zinc-500 text-[10px] text-center leading-relaxed">
            Formulas applied: Mifflin-St Jeor for BMR. BMI is calculated as weight/height². Previews match exact targets to be set in backend.
          </div>
        </div>

      </div>
    </div>
  );
}
