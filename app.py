from flask import Flask, request, jsonify
import boto3
import botocore

app = Flask(__name__)

# Clients AWS
ec2 = boto3.client("ec2")
s3 = boto3.client("s3")

# -----------------------------
# EC2 : Lister les instances
# -----------------------------
@app.route("/ec2", methods=["GET"])
def list_ec2():
    try:
        instances = ec2.describe_instances()
        result = []
        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:
                result.append({
                    "InstanceId": instance["InstanceId"],
                    "State": instance["State"]["Name"],
                    "Type": instance["InstanceType"],
                    "Zone": instance["Placement"]["AvailabilityZone"]
                })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# S3 : Lister les buckets
# -----------------------------
@app.route("/s3", methods=["GET"])
def list_buckets():
    try:
        buckets = [bucket["Name"] for bucket in s3.list_buckets()["Buckets"]]
        return jsonify(buckets), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# S3 : Créer un bucket
# -----------------------------
@app.route("/s3", methods=["POST"])
def create_bucket():
    try:
        data = request.json
        bucket_name = data.get("bucket_name")

        if not bucket_name:
            return jsonify({"error": "bucket_name requis"}), 400

        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": boto3.session.Session().region_name
            }
        )
        return jsonify({"message": f"Bucket {bucket_name} créé avec succès"}), 201
    except botocore.exceptions.ClientError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# S3 : Uploader un fichier
# -----------------------------
@app.route("/s3/upload", methods=["POST"])
def upload_file():
    try:
        data = request.json
        bucket_name = data.get("bucket_name")
        file_path = data.get("file_path")
        object_name = data.get("object_name")

        if not bucket_name or not file_path or not object_name:
            return jsonify({"error": "bucket_name, file_path et object_name sont requis"}), 400

        s3.upload_file(file_path, bucket_name, object_name)

        return jsonify({"message": f"Fichier {object_name} uploadé dans {bucket_name}"}), 200
    except botocore.exceptions.ClientError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# S3 : Supprimer un bucket
# -----------------------------
@app.route("/s3", methods=["DELETE"])
def delete_bucket():
    try:
        data = request.json
        bucket_name = data.get("bucket_name")

        if not bucket_name:
            return jsonify({"error": "bucket_name requis"}), 400

        s3.delete_bucket(Bucket=bucket_name)

        return jsonify({"message": f"Bucket {bucket_name} supprimé avec succès"}), 200
    except botocore.exceptions.ClientError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# Lancer l'app Flask
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
