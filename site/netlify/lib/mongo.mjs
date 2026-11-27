let pending;
export async function database(){
 const uri=process.env.MONGODB_URI;
 const name=process.env.MONGODB_DB||'aether';
 if(!uri||!/^mongodb(?:\+srv)?:\/\//.test(uri)||!/^\w[\w-]{0,62}$/.test(name))throw Error('database_unconfigured');
 if(!pending){
  pending=(async()=>{
   const {MongoClient}=await import('mongodb');
   const client=new MongoClient(uri,{maxPoolSize:5,minPoolSize:0,maxIdleTimeMS:30000,serverSelectionTimeoutMS:5000,connectTimeoutMS:5000,socketTimeoutMS:10000});
   try{
    await client.connect();
    const db=client.db(name);
    await db.collection('demo_projects').createIndex({owner:1,createdAt:-1});
    await db.collection('demo_projects').createIndex({expiresAt:1},{expireAfterSeconds:0});
    await db.collection('workspaces').createIndex({expiresAt:1},{expireAfterSeconds:0});
    await db.collection('accounts').createIndex({userId:1},{unique:true});
    await db.collection('auth_limits').createIndex({expiresAt:1},{expireAfterSeconds:0});
    return db;
   }catch(err){await client.close();throw err;}
  })().catch(err=>{pending=undefined;throw err;});
 }
 return pending;
}
