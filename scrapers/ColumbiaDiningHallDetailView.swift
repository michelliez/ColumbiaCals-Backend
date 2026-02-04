//
//  DiningHallDetailView.swift
//  CalRoarie
//
//  Updated with: macros display, solid blue headers, colored status box
//

import SwiftUI

struct ColumbiaDiningHallDetailView: View {
    let diningHall: DiningHall
    @ObservedObject var cartVM: CartViewModel
    @Environment(\.colorScheme) var colorScheme

    @State private var searchText = ""
    @State private var expandedStations: Set<String> = []
    @State private var scrollToItem: String? = nil
    @State private var selectedMealIndex: Int = 0
    @State private var showBeveragesOverlay = false
    @State private var showRatingSheet = false

    @ObservedObject private var ratingService = RatingService.shared

    // Determine current meal based on scraped time ranges
    private func getCurrentMealIndex() -> Int {
        let now = Date()
        let calendar = Calendar.current

        // Check if current time falls within any meal's time range
        for (index, meal) in diningHall.meals.enumerated() {
            if isCurrentTimeInMeal(meal: meal, now: now, calendar: calendar) {
                return index
            }
        }

        // If not currently in any meal period, find the next upcoming meal
        for (index, meal) in diningHall.meals.enumerated() {
            if isMealUpcoming(meal: meal, now: now, calendar: calendar) {
                return index
            }
        }

        // Default to first meal if no match found
        return 0
    }

    private func isCurrentTimeInMeal(meal: Meal, now: Date, calendar: Calendar) -> Bool {
        guard let (startTime, endTime) = parseTimeRange(meal.time) else { return false }

        let currentHour = calendar.component(.hour, from: now)
        let currentMinute = calendar.component(.minute, from: now)
        let currentTotalMinutes = currentHour * 60 + currentMinute

        let startTotalMinutes = startTime.hour * 60 + startTime.minute
        let endTotalMinutes = endTime.hour * 60 + endTime.minute

        return currentTotalMinutes >= startTotalMinutes && currentTotalMinutes < endTotalMinutes
    }

    private func isMealUpcoming(meal: Meal, now: Date, calendar: Calendar) -> Bool {
        guard let (startTime, _) = parseTimeRange(meal.time) else { return false }

        let currentHour = calendar.component(.hour, from: now)
        let currentMinute = calendar.component(.minute, from: now)
        let currentTotalMinutes = currentHour * 60 + currentMinute

        let startTotalMinutes = startTime.hour * 60 + startTime.minute

        return currentTotalMinutes < startTotalMinutes
    }

    private func parseTimeRange(_ timeString: String) -> ((hour: Int, minute: Int), (hour: Int, minute: Int))? {
        // Parse "11:00 AM - 4:00 PM" format
        let components = timeString.components(separatedBy: " - ")
        guard components.count == 2 else { return nil }

        let startTime = parseTime(components[0].trimmingCharacters(in: .whitespaces))
        let endTime = parseTime(components[1].trimmingCharacters(in: .whitespaces))

        guard let start = startTime, let end = endTime else { return nil }
        return (start, end)
    }

    private func parseTime(_ timeString: String) -> (hour: Int, minute: Int)? {
        // Parse "11:00 AM" or "4:00 PM" format
        let components = timeString.components(separatedBy: " ")
        guard components.count == 2 else { return nil }

        let timeParts = components[0].components(separatedBy: ":")
        guard timeParts.count == 2,
              var hour = Int(timeParts[0]),
              let minute = Int(timeParts[1]) else { return nil }

        let isPM = components[1].uppercased() == "PM"

        // Convert to 24-hour format
        if isPM && hour != 12 {
            hour += 12
        } else if !isPM && hour == 12 {
            hour = 0
        }

        return (hour, minute)
    }
    
    var body: some View {
        ZStack {
            Color.appBackground
                .ignoresSafeArea()
            
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        // Header with colored status box
                        headerView

                        // Content based on status
                        if diningHall.shouldShowItems {
                            // Meal tabs
                            if diningHall.meals.count > 1 {
                                mealTabs
                            }

                            // Show selected meal
                            if diningHall.meals.indices.contains(selectedMealIndex) {
                                MealSectionView(
                                    meal: diningHall.meals[selectedMealIndex],
                                    cartVM: cartVM,
                                    searchText: searchText,
                                    expandedStations: $expandedStations
                                )
                            }
                        } else {
                            // Show status message
                            statusMessageView
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 100)
                }
                .onChange(of: searchText) { newValue in
                    if !newValue.isEmpty {
                        // Expand all stations when searching
                        for meal in diningHall.meals {
                            for station in meal.stations {
                                expandedStations.insert(station.id.uuidString)
                            }
                        }
                        
                        // Find first matching item and scroll to it
                        if let firstMatch = findFirstMatchingItem(query: newValue) {
                            withAnimation {
                                proxy.scrollTo(firstMatch, anchor: .top)
                            }
                        }
                    }
                }
            }

            // Floating Bottom Search Bar with Beverages Button
            VStack {
                Spacer()
                HStack(spacing: 10) {
                    // Search Bar
                    HStack(spacing: 8) {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: 16))
                            .foregroundColor(.textSecondary)

                        TextField("Search menu...", text: $searchText)
                            .font(.system(size: 15))
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 25)
                            .fill(Color.cardBackground)
                            .shadow(color: Color.black.opacity(0.15), radius: 12, x: 0, y: 4)
                    )

                    // Beverages Button
                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                            showBeveragesOverlay.toggle()
                        }
                    } label: {
                        ZStack {
                            Circle()
                                .fill(
                                    LinearGradient(
                                        gradient: Gradient(colors: [
                                            Color.accentRed,
                                            Color.accentRed.opacity(0.85)
                                        ]),
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                                .frame(width: 48, height: 48)
                                .shadow(color: Color.accentRed.opacity(0.4), radius: 8, x: 0, y: 4)

                            Image(systemName: "cup.and.saucer.fill")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundColor(.white)
                        }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 12)
            }

            // Beverages Overlay
            if showBeveragesOverlay {
                FreestyleBeveragesOverlay(
                    cartVM: cartVM,
                    isPresented: $showBeveragesOverlay
                )
                .transition(.opacity.combined(with: .scale(scale: 0.9, anchor: .bottom)))
            }
        }
        .navigationTitle(diningHall.name)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showRatingSheet) {
            RatingSheet(
                hallName: diningHall.name,
                university: "columbia",
                isPresented: $showRatingSheet
            )
            .presentationDetents([.medium])
        }
        .onAppear {
            // Set initial meal based on current time
            selectedMealIndex = getCurrentMealIndex()

            // Expand all stations by default
            for meal in diningHall.meals {
                for station in meal.stations {
                    expandedStations.insert(station.id.uuidString)
                }
            }
        }
    }
    
    // MARK: - Find First Matching Item
    func findFirstMatchingItem(query: String) -> String? {
        for meal in diningHall.meals {
            for station in meal.stations {
                for item in station.items {
                    if item.name.localizedCaseInsensitiveContains(query) {
                        return item.id.uuidString
                    }
                }
            }
        }
        return nil
    }
    
    // MARK: - Header View (Enhanced with gradients and stats)
    var headerView: some View {
        // Determine if the selected meal is currently serving
        let selectedMealIsServing: Bool = {
            guard diningHall.meals.indices.contains(selectedMealIndex) else { return false }
            return isMealCurrentlyServing(meal: diningHall.meals[selectedMealIndex])
        }()
        let headerStatusColor = selectedMealIsServing ? Color.accentGreen : Color.accentRed
        let headerStatusText = selectedMealIsServing ? "Open" : "Closed"

        return VStack(spacing: 16) {
            // Hero Card with Gradient
            VStack(spacing: 0) {
                // Status Badge at top
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(Color.white)
                            .frame(width: 8, height: 8)

                        Text(headerStatusText)
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 7)
                    .background(
                        Capsule()
                            .fill(Color.white.opacity(0.25))
                    )

                    Spacer()
                }
                .padding(.bottom, 20)

                // Meal Type - Big and Bold
                if diningHall.meals.indices.contains(selectedMealIndex) {
                    let meal = diningHall.meals[selectedMealIndex]
                    VStack(spacing: 12) {
                        Text(meal.meal_type)
                            .font(.system(size: 36, weight: .black))
                            .foregroundColor(.white)

                        // Time with icon
                        HStack(spacing: 8) {
                            Image(systemName: "clock.fill")
                                .font(.system(size: 14))

                            Text(meal.time)
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .foregroundColor(.white.opacity(0.9))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(
                            Capsule()
                                .fill(Color.white.opacity(0.2))
                        )
                    }
                }
            }
            .frame(maxWidth: .infinity)
            .padding(24)
            .background(
                ZStack {
                    // Gradient background
                    LinearGradient(
                        gradient: Gradient(colors: [
                            headerStatusColor,
                            headerStatusColor.opacity(0.8)
                        ]),
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )

                    // Decorative circles
                    Circle()
                        .fill(Color.white.opacity(0.1))
                        .frame(width: 150, height: 150)
                        .offset(x: -60, y: -40)

                    Circle()
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 100, height: 100)
                        .offset(x: 80, y: 60)
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: 24))
            .shadow(color: headerStatusColor.opacity(0.3), radius: 20, x: 0, y: 10)

            // Quick Stats Row
            if diningHall.totalItemCount > 0 && diningHall.meals.indices.contains(selectedMealIndex) {
                let selectedMeal = diningHall.meals[selectedMealIndex]
                HStack(spacing: 12) {
                    QuickStatBadge(
                        icon: "fork.knife",
                        value: "\(selectedMeal.totalItemCount)",
                        label: "Items",
                        color: .columbiaBluePrimary
                    )

                    QuickStatBadge(
                        icon: "building.2.fill",
                        value: "\(selectedMeal.stations.count)",
                        label: "Stations",
                        color: .accentOrange
                    )

                    // Rating Badge (replaces Fresh Today)
                    Button {
                        showRatingSheet = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "star.fill")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundColor(.yellow)

                            VStack(alignment: .leading, spacing: 2) {
                                if let rating = ratingService.getRating(for: diningHall.name, university: "columbia") {
                                    Text(String(format: "%.1f", rating.average))
                                        .font(.system(size: 16, weight: .bold))
                                        .foregroundColor(.textPrimary)
                                } else {
                                    Text("-.-")
                                        .font(.system(size: 16, weight: .bold))
                                        .foregroundColor(.textSecondary)
                                }

                                Text("Rate")
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundColor(.textSecondary)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .padding(.horizontal, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color.yellow.opacity(0.2))
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.yellow.opacity(0.5), lineWidth: 1.5)
                        )
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
        }
        .padding(.top, 8)
    }

    // Check if a meal is currently serving
    private func isMealCurrentlyServing(meal: Meal) -> Bool {
        let now = Date()
        let calendar = Calendar.current
        return isCurrentTimeInMeal(meal: meal, now: now, calendar: calendar)
    }

    // MARK: - Meal Tabs
    var mealTabs: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(diningHall.meals.indices, id: \.self) { index in
                    let meal = diningHall.meals[index]
                    let isServing = isMealCurrentlyServing(meal: meal)

                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                            selectedMealIndex = index
                        }
                    } label: {
                        VStack(spacing: 6) {
                            // Meal name with status indicator
                            HStack(spacing: 6) {
                                Text(meal.meal_type)
                                    .font(.system(size: 15, weight: selectedMealIndex == index ? .bold : .semibold))
                                    .foregroundColor(selectedMealIndex == index ? .white : .textPrimary)

                                // Status dot
                                Circle()
                                    .fill(isServing ? Color.accentGreen : Color.accentRed)
                                    .frame(width: 6, height: 6)
                            }

                            Text(meal.time)
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(selectedMealIndex == index ? .white.opacity(0.8) : .textSecondary)

                            // Open/Closed label
                            Text(isServing ? "Open" : "Closed")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(selectedMealIndex == index ? (isServing ? .accentGreen : .white.opacity(0.7)) : (isServing ? .accentGreen : .accentRed))
                        }
                        .frame(minWidth: 110)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(selectedMealIndex == index ?
                                    LinearGradient(
                                        gradient: Gradient(colors: [
                                            Color.columbiaBluePrimary,
                                            Color.columbiaBluePrimary.opacity(0.85)
                                        ]),
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ) :
                                    LinearGradient(
                                        gradient: Gradient(colors: [
                                            Color.cardBackground,
                                            Color.cardBackground
                                        ]),
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(selectedMealIndex == index ? Color.clear : Color.textSecondary.opacity(0.1), lineWidth: 1)
                        )
                        .shadow(color: selectedMealIndex == index ? Color.columbiaBluePrimary.opacity(0.3) : Color.clear, radius: 8, x: 0, y: 4)
                    }
                }
            }
            .padding(.horizontal)
        }
    }

    // MARK: - Status Message View
    var statusMessageView: some View {
        VStack(spacing: 16) {
            Image(systemName: diningHall.statusIcon)
                .font(.system(size: 48))
                .foregroundColor(diningHall.statusColor)

            Text(diningHall.statusMessage)
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(Color.textPrimary)
                .multilineTextAlignment(.center)

            if diningHall.isServiceDown {
                Text("The dining website is temporarily unavailable. Please try again later.")
                    .font(.subheadline)
                    .foregroundColor(Color.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            } else if diningHall.hasNoMenu {
                Text("The dining hall is open, but the menu hasn't been posted yet. Check back soon!")
                    .font(.subheadline)
                    .foregroundColor(Color.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            } else if diningHall.isClosed {
                Text("Check back during dining hours to see what's available.")
                    .font(.subheadline)
                    .foregroundColor(Color.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }

            // Show operating hours if available
            if let hours = diningHall.displayHours, !hours.isEmpty {
                VStack(spacing: 8) {
                    Divider()
                        .padding(.vertical, 8)

                    HStack(spacing: 6) {
                        Image(systemName: "clock")
                            .font(.system(size: 14))
                            .foregroundColor(.columbiaBluePrimary)

                        Text("Operating Hours")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(.columbiaBluePrimary)
                    }

                    Text(hours)
                        .font(.system(size: 13))
                        .foregroundColor(Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }
}

// MARK: - Meal Section View
private struct MealSectionView: View {
    let meal: Meal
    @ObservedObject var cartVM: CartViewModel
    let searchText: String
    @Binding var expandedStations: Set<String>
    
    var filteredStations: [(original: Station, filtered: Station)] {
        if searchText.isEmpty {
            return meal.stations.map { ($0, $0) }
        }
        
        return meal.stations.compactMap { station in
            let matchingItems = station.items.filter { item in
                item.name.localizedCaseInsensitiveContains(searchText)
            }
            
            if matchingItems.isEmpty {
                return nil
            }
            
            let filteredStation = Station(station: station.station, items: matchingItems)
            return (station, filteredStation)
        }
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Stations (meal header removed - it's now in the top status card)
            ForEach(filteredStations, id: \.original.id) { original, filtered in
                StationView(
                    station: filtered,
                    stationId: original.id.uuidString,
                    cartVM: cartVM,
                    isExpanded: expandedStations.contains(original.id.uuidString),
                    onToggle: {
                        if expandedStations.contains(original.id.uuidString) {
                            expandedStations.remove(original.id.uuidString)
                        } else {
                            expandedStations.insert(original.id.uuidString)
                        }
                    }
                )
            }
        }
    }
}

// MARK: - Station View (Solid Blue Header)
private struct StationView: View {
    let station: Station
    let stationId: String
    @ObservedObject var cartVM: CartViewModel
    let isExpanded: Bool
    let onToggle: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Station header - Enhanced with gradient
            Button(action: onToggle) {
                HStack(spacing: 12) {
                    // Icon with background
                    ZStack {
                        Circle()
                            .fill(Color.white.opacity(0.2))
                            .frame(width: 32, height: 32)

                        Image(systemName: "fork.knife")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(station.station)
                            .font(.system(size: 17, weight: .bold))
                            .foregroundColor(.white)

                        Text("\(station.items.count) items available")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.white.opacity(0.8))
                    }

                    Spacer()

                    Image(systemName: isExpanded ? "chevron.up.circle.fill" : "chevron.down.circle.fill")
                        .font(.system(size: 22))
                        .foregroundColor(.white.opacity(0.9))
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 16)
                .background(
                    ZStack {
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color.columbiaBluePrimary,
                                Color.columbiaBluePrimary.opacity(0.85)
                            ]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )

                        // Subtle pattern
                        Circle()
                            .fill(Color.white.opacity(0.05))
                            .frame(width: 80, height: 80)
                            .offset(x: -30, y: 0)
                    }
                )
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .shadow(color: Color.columbiaBluePrimary.opacity(0.3), radius: 8, x: 0, y: 4)
            }
            .buttonStyle(.plain)

            // Items (shown when expanded)
            if isExpanded {
                VStack(spacing: 10) {
                    ForEach(station.items) { item in
                        MenuItemCard(
                            menuItem: item,
                            cartVM: cartVM
                        )
                        .id(item.id.uuidString) // For scrolling
                    }
                }
                .padding(.top, 4)
            }
        }
    }
}

// MARK: - Menu Item Card (WITH MACROS)
private struct MenuItemCard: View {
    let menuItem: MenuItem
    @ObservedObject var cartVM: CartViewModel
    @State private var showingServingSelector = false

    // Food-specific serving size (in natural units)
    private var servingSize: String {
        let name = menuItem.name.lowercased()

        // Proteins
        if name.contains("chicken") || name.contains("fish") || name.contains("salmon") || name.contains("steak") || name.contains("beef") {
            return "1 piece (4 oz)"
        }
        // Pizza
        else if name.contains("pizza") {
            return "1 slice"
        }
        // Grains/Sides
        else if name.contains("rice") || name.contains("pasta") {
            return "1 bowl"
        }
        else if name.contains("bread") || name.contains("roll") || name.contains("biscuit") {
            return "1 piece"
        }
        // Vegetables
        else if name.contains("vegetable") || name.contains("broccoli") || name.contains("spinach") || name.contains("salad") {
            return "1 cup"
        }
        // Tacos/Wraps
        else if name.contains("taco") || name.contains("burrito") || name.contains("wrap") || name.contains("sandwich") {
            return "1 piece"
        }
        // Soup
        else if name.contains("soup") || name.contains("chowder") {
            return "1 bowl"
        }
        // Dessert
        else if name.contains("cookie") || name.contains("brownie") || name.contains("cake") {
            return "1 piece"
        }
        // Drinks
        else if name.contains("juice") || name.contains("milk") || name.contains("coffee") || name.contains("tea") {
            return "1 cup"
        }
        // Default
        else {
            return "1 serving"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Item name with serving size and add button
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(menuItem.name)
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(Color.textPrimary)

                        Text("•")
                            .font(.system(size: 13))
                            .foregroundColor(Color.textSecondary)

                        Text(servingSize)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundColor(Color.textSecondary)
                    }

                    // Description (if available)
                    if let description = menuItem.description, !description.isEmpty {
                        Text(description)
                            .font(.system(size: 13))
                            .foregroundColor(Color.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                Spacer()

                // Add button
                Button {
                    showingServingSelector = true
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 28))
                        .foregroundColor(Color.columbiaBluePrimary)
                }
            }

            // MACROS ROW - Large badges with colored backgrounds
            HStack(spacing: 8) {
                MacroBadgeLarge(
                    value: menuItem.calories != nil ? "\(menuItem.calories!)" : "—",
                    label: "Cal",
                    color: Color.calorieColor
                )

                MacroBadgeLarge(
                    value: menuItem.protein != nil ? "\(menuItem.protein!)g" : "—",
                    label: "Protein",
                    color: Color.proteinColor
                )

                MacroBadgeLarge(
                    value: menuItem.carbs != nil ? "\(menuItem.carbs!)g" : "—",
                    label: "Carbs",
                    color: Color.carbsColor
                )

                MacroBadgeLarge(
                    value: menuItem.fat != nil ? "\(menuItem.fat!)g" : "—",
                    label: "Fat",
                    color: Color.fatColor
                )
            }

            // Dietary preferences and allergens
            if !menuItem.dietary_prefs.isEmpty || !menuItem.allergens.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        // Dietary badges
                        ForEach(menuItem.dietary_prefs, id: \.self) { pref in
                            DietaryBadge(preference: pref)
                        }

                        // Allergen warning
                        if !menuItem.allergens.isEmpty {
                            HStack(spacing: 4) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .font(.caption2)
                                Text(menuItem.allergens.joined(separator: ", "))
                                    .font(.caption2)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(
                                Capsule()
                                    .fill(Color.accentOrange.opacity(0.2))
                            )
                            .foregroundColor(Color.accentOrange)
                        }
                    }
                }
            }

            // Estimated label
            if menuItem.estimated == true {
                Text("Estimated")
                    .font(.system(size: 11))
                    .foregroundColor(Color.textSecondary.opacity(0.7))
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.cardBackground)
        )
        .sheet(isPresented: $showingServingSelector) {
            ServingSelectorSheet(menuItem: menuItem, cartVM: cartVM, foodSpecificServing: servingSize)
        }
    }
}

// MARK: - Large Macro Badge (for item cards - matches screenshot aesthetic)
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
                .foregroundColor(Color.textSecondary)
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

// MARK: - Dietary Badge
private struct DietaryBadge: View {
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

// MARK: - Quick Stat Badge
private struct QuickStatBadge: View {
    let icon: String
    let value: String
    let label: String
    let color: Color

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(color)

            VStack(alignment: .leading, spacing: 2) {
                Text(value)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.textPrimary)

                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.textSecondary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .padding(.horizontal, 12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.cardBackground)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(color.opacity(0.2), lineWidth: 1.5)
        )
    }
}

// MARK: - Freestyle Beverages Overlay
private struct FreestyleBeveragesOverlay: View {
    @ObservedObject var cartVM: CartViewModel
    @Binding var isPresented: Bool
    @State private var searchText = ""

    private var filteredBeverages: [MenuItem] {
        if searchText.isEmpty {
            return FreestyleBeverages.allBeverages
        }
        return FreestyleBeverages.allBeverages.filter { item in
            item.name.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        ZStack {
            // Dimmed background
            Color.black.opacity(0.4)
                .ignoresSafeArea()
                .onTapGesture {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        isPresented = false
                    }
                }

            // Overlay card
            VStack(spacing: 0) {
                // Header
                HStack {
                    Image(systemName: "cup.and.saucer.fill")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)

                    Text("Coca-Cola Freestyle")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)

                    Spacer()

                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                            isPresented = false
                        }
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(.white.opacity(0.8))
                    }
                }
                .padding(16)
                .background(
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color.accentRed,
                            Color.accentRed.opacity(0.9)
                        ]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

                // Search bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.textSecondary)
                    TextField("Search drinks...", text: $searchText)
                        .font(.system(size: 14))
                }
                .padding(10)
                .background(Color.elevatedBackground)
                .cornerRadius(8)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.cardBackground)

                // Beverages list
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(filteredBeverages) { item in
                            CompactBeverageCard(menuItem: item, cartVM: cartVM)
                        }
                    }
                    .padding(12)
                }
                .background(Color.appBackground)
            }
            .frame(maxWidth: .infinity, maxHeight: UIScreen.main.bounds.height * 0.6)
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .shadow(color: Color.black.opacity(0.3), radius: 20, x: 0, y: 10)
            .padding(.horizontal, 16)
            .padding(.bottom, 80)
        }
    }
}

// MARK: - Compact Beverage Card (Small cards for overlay)
private struct CompactBeverageCard: View {
    let menuItem: MenuItem
    @ObservedObject var cartVM: CartViewModel
    @State private var showingServingSelector = false

    var body: some View {
        HStack(spacing: 12) {
            // Beverage info
            VStack(alignment: .leading, spacing: 2) {
                Text(menuItem.name)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.textPrimary)
                    .lineLimit(1)

                // Calorie badge inline
                HStack(spacing: 4) {
                    Text("\(menuItem.calories ?? 0)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.calorieColor)
                    Text("cal")
                        .font(.system(size: 11))
                        .foregroundColor(.textSecondary)

                    if menuItem.calories == 0 {
                        Text("• Sugar Free")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.accentGreen)
                    }
                }
            }

            Spacer()

            // Add button
            Button {
                showingServingSelector = true
            } label: {
                Image(systemName: "plus.circle.fill")
                    .font(.system(size: 24))
                    .foregroundColor(.accentRed)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.cardBackground)
        )
        .sheet(isPresented: $showingServingSelector) {
            ServingSelectorSheet(menuItem: menuItem, cartVM: cartVM, foodSpecificServing: "12 oz")
        }
    }
}

// MARK: - Preview
#Preview {
    NavigationView {
        ColumbiaDiningHallDetailView(
            diningHall: DiningHall.sampleOpen,
            cartVM: CartViewModel()
        )
    }
    .preferredColorScheme(.dark)
}