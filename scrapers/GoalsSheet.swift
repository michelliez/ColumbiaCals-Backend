import SwiftUI

struct GoalsSheet: View {

    @ObservedObject var cartVM: CartViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationView {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recommended Daily Goals")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.textPrimary)
                        
                        HStack(spacing: 20) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Male")
                                    .font(.caption)
                                    .foregroundColor(.textSecondary)
                                Text("2500 cal • 150g protein")
                                    .font(.caption)
                                    .foregroundColor(.textSecondary)
                            }
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Female")
                                    .font(.caption)
                                    .foregroundColor(.textSecondary)
                                Text("2000 cal • 120g protein")
                                    .font(.caption)
                                    .foregroundColor(.textSecondary)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
                
                Section(header: Text("Daily Goals")) {
                    Stepper(
                        value: $cartVM.calorieLimit,
                        in: 1000...5000,
                        step: 50
                    ) {
                        HStack {
                            Text("Calories")
                            Spacer()
                            Text("\(cartVM.calorieLimit)")
                                .foregroundColor(.calorieColor)
                                .fontWeight(.semibold)
                        }
                    }

                    Stepper(
                        value: $cartVM.proteinGoal,
                        in: 20...300,
                        step: 5
                    ) {
                        HStack {
                            Text("Protein")
                            Spacer()
                            Text("\(cartVM.proteinGoal)g")
                                .foregroundColor(.proteinColor)
                                .fontWeight(.semibold)
                        }
                    }
                }
            }
            .navigationTitle("Daily Goals")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}
