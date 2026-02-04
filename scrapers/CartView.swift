//
//  CartView.swift
//  CalRoarie
//
//  Updated with dietary badges on cart items
//

import SwiftUI

struct CartView: View {
    @ObservedObject var cartVM: CartViewModel
    @StateObject private var streakManager = StreakManager()
    @State private var showingGoalsSheet = false
    @State private var showingCustomFoodSheet = false
    @State private var showingCheckoutAlert = false
    @Environment(\.colorScheme) var colorScheme
    
    var calorieProgress: Double {
        Double(cartVM.totalCalories) / Double(cartVM.calorieLimit)
    }
    
    var proteinProgress: Double {
        Double(cartVM.totalProtein) / Double(cartVM.proteinGoal)
    }
    
    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient.appBackgroundGradient
                .ignoresSafeArea()

            cartContent
        }
        .navigationTitle("My Cart")
        .toolbar {
            if !cartVM.cartItems.isEmpty {
                ToolbarItem(placement: .automatic) {
                    Button("Clear All") {
                        cartVM.clearCart()
                    }
                    .foregroundColor(.accentRed)
                }
            }
        }
        .sheet(isPresented: $showingGoalsSheet) {
            GoalsSheet(cartVM: cartVM)
        }
        .sheet(isPresented: $showingCustomFoodSheet) {
            CustomFoodSheet(cartVM: cartVM)
        }
        .alert("Day Complete! 🎉", isPresented: $showingCheckoutAlert) {
            Button("Log Day", role: .destructive) {
                cartVM.completeDay()
            }
            Button("Keep Editing", role: .cancel) { }
        } message: {
            let difference = cartVM.totalCalories - cartVM.calorieLimit
            let status = abs(difference) <= 300 ? "On track! 🔥" :
                        difference > 0 ? "Over goal" : "Under goal"
            
            Text("""
            \(status)
            
            Calories: \(cartVM.totalCalories) / \(cartVM.calorieLimit)
            Protein: \(cartVM.totalProtein)g / \(cartVM.proteinGoal)g
            Carbs: \(cartVM.totalCarbs)g • Fat: \(cartVM.totalFat)g
            """)
        }
    }
    
    // MARK: - Cart Content
    var cartContent: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Streak Badge
                StreakBadge(streak: streakManager.currentStreak)
                    .padding(.horizontal)
                    .padding(.top, 20)

                // Progress Rings
                MacroProgressRings(
                    calorieProgress: calorieProgress,
                    proteinProgress: proteinProgress,
                    totalCalories: cartVM.totalCalories,
                    calorieLimit: cartVM.calorieLimit,
                    totalProtein: cartVM.totalProtein,
                    proteinGoal: cartVM.proteinGoal
                )
                .padding(.horizontal)
                .overlay(
                    Button(action: {
                        showingGoalsSheet = true
                    }) {
                        Image(systemName: "pencil.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(.columbiaBluePrimary)
                            .background(
                                Circle()
                                    .fill(Color.cardBackground)
                                    .frame(width: 28, height: 28)
                            )
                    }
                    .padding(.trailing, 24)
                    .padding(.top, 8),
                    alignment: .topTrailing
                )
                
                // Macros Summary
                macrosSummary
                
                // Cart Items
                VStack(spacing: 12) {
                    ForEach(cartVM.cartItems) { item in
                        CartItemCard(cartItem: item, cartVM: cartVM)
                    }
                }
                .padding(.horizontal)
                
                // Action Buttons
                VStack(spacing: 12) {
                    Button {
                        showingCustomFoodSheet = true
                    } label: {
                        HStack {
                            Image(systemName: "plus.circle.fill")
                            Text("Add Custom Food")
                        }
                        .font(.headline)
                        .foregroundColor(.columbiaBluePrimary)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.columbiaBluePrimary, lineWidth: 2)
                        )
                    }
                    
                    Button {
                        showingCheckoutAlert = true
                    } label: {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                            Text("Complete Day")
                        }
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color.accentGreen)
                        )
                    }
                }
                .padding(.horizontal)
                .padding(.bottom, 100)
            }
        }
    }
    
    // MARK: - Macros Summary
    var macrosSummary: some View {
        HStack(spacing: 12) {
            MacroPill(
                label: "Calories",
                value: "\(cartVM.totalCalories)",
                color: .calorieColor
            )
            
            MacroPill(
                label: "Protein",
                value: "\(cartVM.totalProtein)g",
                color: .proteinColor
            )
            
            MacroPill(
                label: "Carbs",
                value: "\(cartVM.totalCarbs)g",
                color: .carbsColor
            )
            
            MacroPill(
                label: "Fat",
                value: "\(cartVM.totalFat)g",
                color: .fatColor
            )
        }
        .padding(.horizontal)
    }
}

// MARK: - Cart Item Card
struct CartItemCard: View {
    @ObservedObject var cartItem: CartItem
    @ObservedObject var cartVM: CartViewModel

    // Only show dietary labels for non-beverage items
    private var shouldShowDietaryLabels: Bool {
        !cartItem.foodItem.isFreestyleBeverage &&
        (!cartItem.foodItem.dietaryPrefs.isEmpty || !cartItem.foodItem.allergens.isEmpty)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Name with serving size and quantity controls
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(cartItem.foodItem.name)
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(.textPrimary)
                            .multilineTextAlignment(.leading)

                        Text("•")
                            .font(.system(size: 13))
                            .foregroundColor(.textSecondary)

                        Text(cartItem.displayServingSize)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundColor(.textSecondary)
                    }
                }

                Spacer()

                HStack(spacing: 10) {
                    Button {
                        cartVM.decrementQuantity(for: cartItem)
                    } label: {
                        Image(systemName: "minus.circle.fill")
                            .foregroundColor(.accentRed)
                            .font(.title3)
                    }
                    .buttonStyle(.plain)

                    Text("\(cartItem.quantity)")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.textPrimary)
                        .frame(minWidth: 24)

                    Button {
                        cartVM.incrementQuantity(for: cartItem)
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .foregroundColor(.accentGreen)
                            .font(.title3)
                    }
                    .buttonStyle(.plain)
                }
            }

            // MACROS ROW - Large badges with colored backgrounds (matching detail view)
            HStack(spacing: 8) {
                MacroBadgeLarge(
                    value: "\(cartItem.totalCalories)",
                    label: "Cal",
                    color: .calorieColor
                )

                MacroBadgeLarge(
                    value: "\(cartItem.totalProtein)g",
                    label: "Protein",
                    color: .proteinColor
                )

                MacroBadgeLarge(
                    value: "\(cartItem.totalCarbs)g",
                    label: "Carbs",
                    color: .carbsColor
                )

                MacroBadgeLarge(
                    value: "\(cartItem.totalFat)g",
                    label: "Fat",
                    color: .fatColor
                )
            }

            // Dietary badges - only for food items, NOT beverages
            if shouldShowDietaryLabels {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        // Dietary preferences
                        ForEach(cartItem.foodItem.dietaryPrefs, id: \.self) { pref in
                            DietaryBadgeSmall(preference: pref)
                        }

                        // Allergen warnings
                        if !cartItem.foodItem.allergens.isEmpty {
                            HStack(spacing: 4) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .font(.caption2)
                                Text(cartItem.foodItem.allergens.joined(separator: ", "))
                                    .font(.caption2)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(
                                Capsule()
                                    .fill(Color.accentOrange.opacity(0.2))
                            )
                            .foregroundColor(.accentOrange)
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.cardBackground)
        )
    }
}

// MARK: - Large Macro Badge (matching detail view)
private struct MacroBadgeLarge: View {
    let value: String
    let label: String
    let color: Color

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(color)

            Text(label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 6)
        .padding(.horizontal, 6)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(color.opacity(0.12))
        )
    }
} 

// MARK: - Dietary Badge Small (for cart items)
struct DietaryBadgeSmall: View {
    let preference: String

    var body: some View {
        HStack(spacing: 4) {
            if !icon.isEmpty {
                Text(icon)
                    .font(.system(size: 11))
            }
            Text(preference)
                .font(.system(size: 11, weight: .medium))
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            Capsule()
                .fill(color.opacity(0.2))
        )
        .foregroundColor(color)
    }

    var icon: String {
        switch preference.lowercased() {
        case "vegan": return "🌱"
        case "vegetarian": return "🥬"
        case "gluten free": return "🌾"
        case "halal": return ""
        case "kosher": return "✡️"
        case "healthy": return "❤️"
        default: return ""
        }
    }

    var color: Color {
        switch preference.lowercased() {
        case "vegan", "vegetarian": return .accentGreen
        case "gluten free": return .accentBlue
        case "halal", "kosher": return .purple
        case "healthy": return .accentRed
        default: return .textSecondary
        }
    }
}

// MARK: - Macro Badge Compact (for cart items)
struct MacroBadgeCompact: View {
    let label: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 0) {
            Text(value)
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(color)
            
            Text(label)
                .font(.system(size: 7))
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }
} 

// MARK: - Macro Pill (for summary)
struct MacroPill: View {
    let label: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(color)
            
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 6)
        .padding(.horizontal, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(color.opacity(0.12))
        )
    }
} 

#Preview {
    NavigationView {
        CartView(cartVM: CartViewModel())
    }
    .preferredColorScheme(.dark)
}