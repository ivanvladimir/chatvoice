
(function main() {
    // Set our main variables
    let scene,
      socket,  
      renderer,
      camera,
      possibleAnims,
      availableAnimations,
      currentMixer,
      currentAnimation,                              
      currentVrm,                               
      blinky,                                                     
      animAvailable,                               // Idle, the default state our character returns to
      clock = new THREE.Clock(),          // Used for anims, which run to a clock instead of frame rate 
               // Used to check whether characters neck is being used in another anim
      loaderAnim = document.getElementById('js-loader');
      
    

      init();
    

    function init() {

        const model_url = window.location.protocol + '//' + window.location.hostname +  ":" +window.location.port+ '/static/';
        const MODEL_PATH = model_url+'model/merus.vrm';
        //const MODEL_PATH = model_url+'model/johndoe.vrm';
        //use in case the models are not being found by the script, just to locate your actual directory
        const canvas = document.getElementById('c');
        //var path = document.location.pathname;
        //var directory = path.substring(path.indexOf('/'), path.lastIndexOf('/'));
        //console.log(path);
        //console.log(directory);

        //const backgroundColor = 0x5f899c;
        console.log("test");
        console.log(canvas);
        scene = new THREE.Scene();
        //scene.background = new THREE.Color(backgroundColor);
        //scene.fog = new THREE.Fog(backgroundColor, 90, 100);

        renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
        renderer.shadowMap.enabled = true;
        renderer.setPixelRatio(window.devicePixelRatio); 
        document.body.appendChild(renderer.domElement);
        // Add a camera, for meru 35 will display the full body camera, 10 is good enough for face
        // as johndoe is taller, you will need to move the camera higher on y
        camera = new THREE.PerspectiveCamera(10,window.innerWidth / window.innerHeight,0.1,200.0);
        //meru uses 1.3, john doe 1.7
        camera.position.set( 0.0, 1.3, 4.3 );
        //camera.position.set( 0.0, 1.7, 4.3 );
        


        // Add lights

        let hemiLight = new THREE.HemisphereLight(0xffffff, 0xffffff, 1.2);
    hemiLight.position.set(0, 20, 0);
    // Add hemisphere light to scene
    scene.add(hemiLight);

         const light = new THREE.DirectionalLight( 0xffffff, 0.85 );
			light.position.set( 1.0, 1.0, 1.0 ).normalize();
      scene.add( light ); 
     

     

        // Floor
        let floorGeometry = new THREE.PlaneGeometry(5000, 5000, 1, 1);
        let floorMaterial = new THREE.MeshPhongMaterial({
        color: 0xff0000,
        shininess: 0,
        });

        let floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -0.5 * Math.PI; // This is 90 degrees by the way
        floor.receiveShadow = true;
        floor.position.y = -11;
        scene.add(floor); 

/*         let stacy_txt = new THREE.TextureLoader().load('https://s3-us-west-2.amazonaws.com/s.cdpn.io/1376484/stacy.jpg');
        stacy_txt.flipY = false; // we flip the texture so that its the right way up

        const stacy_mtl = new THREE.MeshPhongMaterial({
          map: stacy_txt,
          skinning: true
}); */
          const loader = new THREE.GLTFLoader();
          loader.crossOrigin = 'anonymous';

          

        loader.load(MODEL_PATH,
          (gltf) => {/* 
            model = gltf.scene;
            let fileAnimations = gltf.animations;
            model.traverse(o => {
              if (o.isMesh) {
                o.castShadow = true;
                o.receiveShadow = true;
                o.material = stacy_mtl;
              }
            });
            model.scale.set(7, 7, 7);
            model.position.y = -11;
            scene.add(model);
            loaderAnim.remove();

            mixer = new THREE.AnimationMixer(model);
            let clips = fileAnimations.filter(val => val.name !== 'idle');
            possibleAnims = clips.map(val => {
              let clip = THREE.AnimationClip.findByName(clips, val.name);
              clip = mixer.clipAction(clip);
              return clip;
             });
            let idleAnim = THREE.AnimationClip.findByName(fileAnimations, 'idle');
            idle = mixer.clipAction(idleAnim);
            idle.play(); */

            // generate a VRM instance from gltf
        THREE.VRMUtils.removeUnnecessaryJoints( gltf.scene );

        THREE.VRM.from( gltf ).then( ( vrm ) => {

          // add the loaded vrm to the scene
          console.log( vrm );
          scene.add( vrm.scene );
          pose = {
            [THREE.VRMSchema.HumanoidBoneName.LeftUpperArm] : {
              rotation: [  0.000,  0.000, 0.59,  0.891 ],
              position: [  0.000,  0.000,  0.000 ] // position is not required though
            },
            [THREE.VRMSchema.HumanoidBoneName.RightUpperArm] : {
              rotation: [  0.000,  0.000, -0.59,  0.891 ],
              position: [  0.000,  0.000,  0.000 ]
            },}
          
          vrm.humanoid.setPose(pose);
          

          currentVrm = vrm;

          vrm.humanoid.getBoneNode( THREE.VRMSchema.HumanoidBoneName.Hips ).rotation.y = Math.PI;
          prepareAnimation( vrm );
          loaderAnim.remove();

          // deal with vrm features


		} );

	},

	// called while loading is progressing
	( progress ) => console.log( 'Loading model...', 100.0 * ( progress.loaded / progress.total ), '%' ),

	// called when loading has errors
	( error ) => console.error( error )
        );



    

    }

    function update() {

      const deltaTime = clock.getDelta();

      if ( currentVrm ) {

        currentVrm.update( deltaTime);

      }

      if (currentMixer) {
        currentMixer.update(deltaTime);
      } 
      
     

      if (resizeRendererToDisplaySize(renderer)) {
          const canvas = renderer.domElement;
          camera.aspect = canvas.clientWidth / canvas.clientHeight;
          camera.updateProjectionMatrix();
        }
        renderer.render(scene, camera);
        
        requestAnimationFrame(update);
      }

      update();


      function prepareAnimation( vrm ) {

				currentMixer = new THREE.AnimationMixer( vrm.scene );
        possibleAnims = [];
        availableAnimations = {};

      //if i wanted to rotate... first version of breathing
        /* const quatA = new THREE.Quaternion( 0.0, 0.0, 0.0, 1.0 );
				const quatB = new THREE.Quaternion( 0.0, 0.0, 0.0, 1.0 );
				quatB.setFromEuler( new THREE.Euler( 0.001 * Math.PI, 0.0, 0.0 ) ); 
          
				const breathRotTrack = new THREE.QuaternionKeyframeTrack(
					vrm.humanoid.getBoneNode( THREE.VRMSchema.HumanoidBoneName.Chest ).name + '.quaternion', // name
					[ 0.0, 1.5, 2.5, 3.0, 4.5, 5.5, 6.0 ], // times
					[ ...quatA.toArray(), ...quatB.toArray(), ...quatB.toArray(), ...quatA.toArray(),...quatB.toArray(), ...quatB.toArray(), ...quatA.toArray() ] // values
        );  */

        //breathing with position movement

        const vecA = vrm.humanoid.getBoneNode(THREE.VRMSchema.HumanoidBoneName.Chest).position;
				const vecB = new THREE.Vector3( 0.0, -0.0012, 0.0);
        vecB.add(vecA);
        
        const breathTrack = new THREE.VectorKeyframeTrack(
					vrm.humanoid.getBoneNode( THREE.VRMSchema.HumanoidBoneName.Chest ).name + '.position', // name
					[ 0.0, 1.5, 2.5, 3.0, 4.5, 5.5, 6.0 ], // times
					[ ...vecA.toArray(), ...vecB.toArray(), ...vecB.toArray(), ...vecA.toArray(),...vecB.toArray(), ...vecB.toArray(), ...vecA.toArray() ] // values
        );
        

				const blinkTrack = new THREE.NumberKeyframeTrack(
					vrm.blendShapeProxy.getBlendShapeTrackName( THREE.VRMSchema.BlendShapePresetName.Blink ), // name
					[ 0.0, 0.5, 1.0, 5.0 ], // times
					[ 0.0, 1.0, 0.0, 0.0 ] // values
        );
        var clip = new THREE.AnimationClip( 'blink', -1.0, [  breathTrack, blinkTrack ] );
        currentAnimation = currentMixer.clipAction(clip);
        currentAnimation.setLoop();
        currentAnimation.play();
        animAvailable = true;
        availableAnimations['idle'] = currentMixer.clipAction(clip);
        //possibleAnims.push(blinky);
        
        const angryTrack = new THREE.NumberKeyframeTrack(
					vrm.blendShapeProxy.getBlendShapeTrackName( THREE.VRMSchema.BlendShapePresetName.Angry ), // name
					[ 0.0, 0.5], // times
					[ 1.0, 1.0] // values
        );
        clip = new THREE.AnimationClip( 'angry', 5.0, [breathTrack, angryTrack ] );
        possibleAnims.push(currentMixer.clipAction(clip));
        availableAnimations['angry'] = currentMixer.clipAction(clip);

        
        const funTrack = new THREE.NumberKeyframeTrack(
					vrm.blendShapeProxy.getBlendShapeTrackName( THREE.VRMSchema.BlendShapePresetName.Fun ), // name
					[ 0.0, 0.5], // times
					[ 0.8, 0.8] // values
        );
        clip = new THREE.AnimationClip( 'fun', 5.0, [ breathTrack,funTrack ] );
        possibleAnims.push(currentMixer.clipAction(clip));
        availableAnimations['fun'] = currentMixer.clipAction(clip);

        
        const joyTrack = new THREE.NumberKeyframeTrack(
					vrm.blendShapeProxy.getBlendShapeTrackName( THREE.VRMSchema.BlendShapePresetName.Joy ), // name
					[ 0.0, 0.5], // times
					[ 0.8, 0.8] // values
        );
        clip = new THREE.AnimationClip( 'joy', 5.0, [ breathTrack,joyTrack ] );
        possibleAnims.push(currentMixer.clipAction(clip));
        availableAnimations['joy'] = currentMixer.clipAction(clip);

        
        const sorrowTrack = new THREE.NumberKeyframeTrack(
					vrm.blendShapeProxy.getBlendShapeTrackName( THREE.VRMSchema.BlendShapePresetName.Sorrow ), // name
					[ 0.0, 0.5], // times
					[ 0.6, 0.6] // values
				);
        clip = new THREE.AnimationClip( 'sorrow', 5.0, [breathTrack, sorrowTrack ] );
        possibleAnims.push(currentMixer.clipAction(clip));
        availableAnimations['sorrow'] = currentMixer.clipAction(clip);


				//const clip = new THREE.AnimationClip( 'blink', 1.0, [ blinkTrack ] );
				//const action = currentMixer.clipAction( clip );
				//action.play();
			}


    function resizeRendererToDisplaySize(renderer) {
        const canvas = renderer.domElement;
        let width = canvas.clientWidth;
        let height = canvas.clientHeight;
        let canvasPixelWidth = canvas.width ;
        let canvasPixelHeight = canvas.height ;
      
        const needResize =
          canvasPixelWidth !== width || canvasPixelHeight !== height;
        if (needResize) {
          renderer.setSize(width, height, false);
        }
        return needResize;
      }

      $('#start').click(function(e) {
        socket = window.getSocket();
        console.log(socket);
        
        socket.on('emotion log', function(data) {
          console.log('Animation recieved: ' + data.emotion);
          playAnimation(data.emotion);
        }); 
      });



      //window.addEventListener('click', e => playAnimation('angry'));
      
       


/*       function playAnimation() {
        let anim = Math.floor(Math.random() * possibleAnims.length) + 0;
        if (animAvailable)
        {
          playModifierAnimation(blinky, 0.25, possibleAnims[anim], 0.25);
        }
      } */

     function playAnimation(animationName) {
        if (animAvailable)
        {
          playModifierAnimation(currentAnimation, 0.25, availableAnimations[animationName], 0.25);
          
        }
      }

      function playModifierAnimation(from, fSpeed, to, tSpeed) {
        if (currentAnimation != to){
          animAvailable = false;
          currentAnimation = to;
          to.setLoop(THREE.LoopRepeat);
          to.reset();
          to.play();
          from.crossFadeTo(to, fSpeed, true);
          /* setTimeout(function() {
            from.enabled = true;
            to.crossFadeTo(from, tSpeed, true);
            animAvailable = true;
          }, to._clip.duration * 1000 - ((tSpeed + fSpeed) * 1000)); */
          animAvailable = true;
          from.enabled = true; 
        }
      }


    })(); // Don't add anything below this line
