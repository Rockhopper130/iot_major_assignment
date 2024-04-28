from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
import random
import pickle

features = []
target = []
for t in range(1000):
    features.append(generate_data(t))
    if(t%27<15):
        target.append(1) 
    else: 
        target.append(0)    

selected_features = [(x[1], x[2], x[3]) for x in features]
data = list(zip(selected_features, target))

random.shuffle(data)

X_train, X_test, y_train, y_test = train_test_split([d[0] for d in data], [d[1] for d in data], test_size=0.2, random_state=42)
model = SVC()

model.fit(X_train, y_train)
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

with open('svm_model.pkl', 'wb') as file:
    pickle.dump(model, file)