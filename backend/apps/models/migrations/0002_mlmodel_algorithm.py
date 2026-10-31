from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("models", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="mlmodel",
            name="algorithm",
            field=models.CharField(
                choices=[
                    ("RANDOM_FOREST_CLASSIFIER", "Random Forest Classifier"),
                    ("DECISION_TREE_CLASSIFIER", "Decision Tree Classifier"),
                    ("LOGISTIC_REGRESSION", "Logistic Regression"),
                    ("RANDOM_FOREST_REGRESSOR", "Random Forest Regressor"),
                    ("LINEAR_REGRESSION", "Linear Regression"),
                ],
                default="RANDOM_FOREST_CLASSIFIER",
                max_length=40,
            ),
        ),
    ]
